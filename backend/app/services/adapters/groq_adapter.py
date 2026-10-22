import time
import random
import re
from typing import Optional, Dict, Any
from app.services.adapters.base import BaseAgentAdapter, AgentExecutionResult
from app.core.config import settings
from app.core.logging import logger

# Published standard Groq model pricing (USD per 1M tokens) - (input_rate_per_1m, output_rate_per_1m)
GROQ_MODEL_PRICING: Dict[str, tuple[float, float]] = {
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.3-70b-specdec": (0.59, 0.99),
    "llama-3.1-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "llama3-70b-8192": (0.59, 0.79),
    "llama3-8b-8192": (0.05, 0.08),
    "mixtral-8x7b-32768": (0.24, 0.24),
    "gemma2-9b-it": (0.20, 0.20),
}


def calculate_groq_cost(
    model_name: str,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
) -> Optional[float]:
    """
    Calculates cost in USD if model pricing is published and token counts are available.
    Returns None (unavailable) for preview, custom, or free-tier models.
    """
    if prompt_tokens is None or completion_tokens is None:
        return None

    pricing = GROQ_MODEL_PRICING.get(model_name)
    if not pricing:
        for known_model, rates in GROQ_MODEL_PRICING.items():
            if model_name.startswith(known_model):
                pricing = rates
                break

    if not pricing:
        return None

    input_rate, output_rate = pricing
    total_cost = (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000.0
    return round(total_cost, 6)


class GroqAgentAdapter(BaseAgentAdapter):
    """
    Real LLM provider adapter executing inferences via official Groq Python SDK.
    Captures:
    - Actual response text
    - Provider and model identifier
    - Measured round-trip wall-clock latency (ms)
    - Measured actual token usage from provider (prompt + completion)
    - Calculated cost (USD) based on published rates, or marked unavailable
    - Diagnostic error details on authentication failure, rate limits, timeouts, etc.
    - Never falls back silently to mock adapter.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        client: Optional[Any] = None,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.base_url = base_url or settings.GROQ_BASE_URL
        self.timeout_seconds = timeout_seconds or settings.GROQ_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.GROQ_MAX_RETRIES
        self._client = client

    def _get_client(self) -> Any:
        """Lazily initialize and return Groq SDK client."""
        if self._client is not None:
            return self._client

        if not self.api_key:
            return None

        try:
            import os
            from groq import Groq
            if os.environ.get("GROQ_BASE_URL") == "":
                os.environ.pop("GROQ_BASE_URL", None)

            client_kwargs: Dict[str, Any] = {
                "api_key": self.api_key,
                "timeout": self.timeout_seconds,
                "max_retries": self.max_retries,
            }
            if self.base_url and self.base_url.strip():
                client_kwargs["base_url"] = self.base_url.strip()
            self._client = Groq(**client_kwargs)
            return self._client
        except Exception as exc:
            logger.error("Failed to initialize Groq client: %s", str(exc))
            return None

    @staticmethod
    def _extract_retry_guidance(exc: Any) -> Optional[float]:
        """
        Extracts recommended retry duration (in seconds) from RateLimitError headers or message.
        Checks:
        1. 'retry-after' HTTP header
        2. 'x-ratelimit-reset-requests' / 'x-ratelimit-reset-tokens' HTTP headers
        3. Regex match on exception message (e.g. 'try again in 2.5s')
        """
        response = getattr(exc, "response", None)
        if response is not None:
            headers = getattr(response, "headers", {}) or {}
            # 1. Check retry-after
            val = headers.get("retry-after") or headers.get("Retry-After")
            if val:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
            # 2. Check Groq rate-limit reset headers
            for k in ("x-ratelimit-reset-requests", "x-ratelimit-reset-tokens"):
                val = headers.get(k)
                if val:
                    try:
                        s = str(val).strip().lower()
                        if s.endswith("ms"):
                            return float(s[:-2]) / 1000.0
                        if s.endswith("s"):
                            return float(s[:-1])
                        return float(s)
                    except (ValueError, TypeError):
                        pass

        # 3. Fallback: Parse from exception message
        msg = getattr(exc, "message", None) or str(exc)
        if msg:
            match_s = re.search(r"try again in\s+([0-9.]+)\s*s", msg, re.IGNORECASE)
            if match_s:
                try:
                    return float(match_s.group(1))
                except (ValueError, TypeError):
                    pass
            match_ms = re.search(r"try again in\s+([0-9.]+)\s*ms", msg, re.IGNORECASE)
            if match_ms:
                try:
                    return float(match_ms.group(1)) / 1000.0
                except (ValueError, TypeError):
                    pass

        return None

    def execute(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_name: Optional[str] = None,
        expected_output: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutionResult:
        resolved_model = model_name or settings.GROQ_MODEL

        # 1. Credential Check
        if not self.api_key:
            logger.warning(
                "GroqAgentAdapter: GROQ_API_KEY not configured. Failing case explicitly without mock fallback."
            )
            return AgentExecutionResult(
                output=None,
                latency_ms=0.0,
                token_usage=None,
                prompt_tokens=None,
                completion_tokens=None,
                tokens_estimated=False,
                is_mock=False,
                is_error=True,
                error_message="Groq API key not configured. Set GROQ_API_KEY environment variable to execute real provider evaluations.",
                cost_usd=None,
                model_name=resolved_model,
                model_provider="groq",
                raw_response={"error_type": "missing_api_key", "provider": "groq"},
            )

        client = self._get_client()
        if client is None:
            return AgentExecutionResult(
                output=None,
                latency_ms=0.0,
                token_usage=None,
                prompt_tokens=None,
                completion_tokens=None,
                tokens_estimated=False,
                is_mock=False,
                is_error=True,
                error_message="Failed to initialize Groq client library.",
                cost_usd=None,
                model_name=resolved_model,
                model_provider="groq",
                raw_response={"error_type": "client_initialization_failure", "provider": "groq"},
            )

        # 2. Build Messages Payload
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt})

        # 3. Execute Real API Call with High-Precision Wall-Clock Latency Measurement & Bounded Backoff
        start_perf = time.perf_counter()
        response = None
        max_attempts = 3
        try:
            import groq

            for attempt in range(1, max_attempts + 1):
                try:
                    response = client.chat.completions.create(
                        model=resolved_model,
                        messages=messages,
                        timeout=self.timeout_seconds,
                    )
                    break
                except groq.RateLimitError as rle:
                    if attempt < max_attempts:
                        guidance_s = self._extract_retry_guidance(rle)
                        if guidance_s is not None:
                            # Clamp provider guidance between 1.0s and 8.0s
                            backoff_s = max(1.0, min(float(guidance_s), 8.0))
                        else:
                            # Exponential backoff capped at 6.0s
                            backoff_s = min(1.5 * (2 ** (attempt - 1)), 6.0)

                        jitter = random.uniform(0.1, 0.4)
                        total_sleep = round(backoff_s + jitter, 2)
                        logger.warning(
                            "Groq RateLimitError (429) hit for model '%s'. Respecting provider guidance: "
                            "backing off for %.2fs (attempt %d/%d)...",
                            resolved_model,
                            total_sleep,
                            attempt,
                            max_attempts,
                        )
                        time.sleep(total_sleep)
                        continue
                    raise

            latency_ms = round((time.perf_counter() - start_perf) * 1000.0, 2)

            # 4. Extract Response Content
            choices = getattr(response, "choices", None)
            if not choices or len(choices) == 0:
                return AgentExecutionResult(
                    output=None,
                    latency_ms=latency_ms,
                    token_usage=0,
                    tokens_estimated=False,
                    is_mock=False,
                    is_error=True,
                    error_message="Malformed response: choices list is empty.",
                    cost_usd=None,
                    model_name=resolved_model,
                    model_provider="groq",
                    raw_response={"error_type": "empty_choices", "provider": "groq"},
                )

            first_choice = choices[0]
            output_text = getattr(first_choice.message, "content", None)
            finish_reason = getattr(first_choice, "finish_reason", None)

            # Handle empty/null content
            if output_text is None or output_text.strip() == "":
                return AgentExecutionResult(
                    output="",
                    latency_ms=latency_ms,
                    token_usage=0,
                    tokens_estimated=False,
                    is_mock=False,
                    is_error=True,
                    error_message=f"Empty content received from model (finish_reason: {finish_reason}).",
                    cost_usd=None,
                    model_name=resolved_model,
                    model_provider="groq",
                    raw_response={"finish_reason": finish_reason, "provider": "groq"},
                )

            # 5. Extract Token Usage (Actual from Provider)
            usage = getattr(response, "usage", None)
            tokens_estimated = False
            prompt_tokens = None
            completion_tokens = None
            total_tokens = None
            timing_meta: Dict[str, Any] = {}

            if usage:
                prompt_tokens = getattr(usage, "prompt_tokens", None)
                completion_tokens = getattr(usage, "completion_tokens", None)
                total_tokens = getattr(usage, "total_tokens", None)
                if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
                    total_tokens = prompt_tokens + completion_tokens

                # Groq specific hardware timing telemetries
                for timing_key in ("completion_time", "prompt_time", "queue_time", "total_time"):
                    val = getattr(usage, timing_key, None)
                    if val is not None:
                        timing_meta[timing_key] = val
            else:
                prompt_words = len(prompt.split()) if prompt else 1
                output_words = len(output_text.split()) if output_text else 1
                prompt_tokens = max(1, (prompt_words * 4) // 3)
                completion_tokens = max(1, (output_words * 4) // 3)
                total_tokens = prompt_tokens + completion_tokens
                tokens_estimated = True

            # 6. Calculate Cost (USD) if known, else marked unavailable (None)
            cost_usd = calculate_groq_cost(
                model_name=resolved_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

            raw_meta: Dict[str, Any] = {
                "provider": "groq",
                "model": resolved_model,
                "response_id": getattr(response, "id", None),
                "finish_reason": finish_reason,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "tokens_estimated": tokens_estimated,
                "cost_usd": cost_usd,
            }
            if timing_meta:
                raw_meta["groq_timings"] = timing_meta

            return AgentExecutionResult(
                output=output_text,
                latency_ms=latency_ms,
                token_usage=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                tokens_estimated=tokens_estimated,
                is_mock=False,
                is_error=False,
                error_message=None,
                cost_usd=cost_usd,
                model_name=resolved_model,
                model_provider="groq",
                raw_response=raw_meta,
            )

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_perf) * 1000.0, 2)
            import groq

            error_type = "unknown_error"
            if isinstance(exc, groq.AuthenticationError):
                error_type = "authentication_error"
                diag_msg = f"Invalid Groq API credentials (AuthenticationError): {exc.message}"
            elif isinstance(exc, groq.RateLimitError):
                error_type = "rate_limit_error"
                diag_msg = f"Groq rate limit exceeded (RateLimitError): {exc.message}"
            elif isinstance(exc, groq.APITimeoutError):
                error_type = "timeout_error"
                diag_msg = f"Groq request timed out ({self.timeout_seconds}s limit reached)."
            elif isinstance(exc, groq.APIConnectionError):
                error_type = "connection_error"
                diag_msg = f"Network connection failure to Groq endpoint: {exc.message}"
            elif isinstance(exc, groq.BadRequestError):
                error_type = "bad_request"
                diag_msg = f"Bad request to Groq model API: {exc.message}"
            elif isinstance(exc, groq.InternalServerError):
                error_type = "internal_server_error"
                diag_msg = f"Groq internal service error: {exc.message}"
            elif isinstance(exc, groq.APIError):
                error_type = "api_error"
                diag_msg = f"Groq API error: {exc.message}"
            else:
                diag_msg = f"Unexpected provider error: {str(exc)}"

            logger.error("GroqAgentAdapter execution failed for model %s: %s", resolved_model, diag_msg)

            return AgentExecutionResult(
                output=None,
                latency_ms=latency_ms,
                token_usage=None,
                prompt_tokens=None,
                completion_tokens=None,
                tokens_estimated=False,
                is_mock=False,
                is_error=True,
                error_message=diag_msg,
                cost_usd=None,
                model_name=resolved_model,
                model_provider="groq",
                raw_response={
                    "provider": "groq",
                    "model": resolved_model,
                    "error_type": error_type,
                    "exception_class": type(exc).__name__,
                },
            )
