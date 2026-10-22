import time
from typing import Optional, Dict, Any
from app.services.adapters.base import BaseAgentAdapter, AgentExecutionResult
from app.core.config import settings
from app.core.logging import logger

# Model pricing lookup (USD per 1M tokens) - [input_rate_per_1m, output_rate_per_1m]
OPENAI_MODEL_PRICING: Dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-2024-08-06": (2.50, 10.00),
    "gpt-4o-2024-11-20": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o-mini-2024-07-18": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1": (15.00, 60.00),
    "o1-preview": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    "o3-mini": (1.10, 4.40),
}


def calculate_openai_cost(
    model_name: str,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
) -> Optional[float]:
    """
    Calculates cost in USD if model pricing is known and token counts are available.
    Returns None if pricing is unavailable for the model.
    """
    if prompt_tokens is None or completion_tokens is None:
        return None

    # Exact or prefix match on model name
    pricing = OPENAI_MODEL_PRICING.get(model_name)
    if not pricing:
        # Check prefix match (e.g. gpt-4o-mini-xxx)
        for known_model, rates in OPENAI_MODEL_PRICING.items():
            if model_name.startswith(known_model):
                pricing = rates
                break

    if not pricing:
        return None

    input_rate, output_rate = pricing
    total_cost = (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000.0
    return round(total_cost, 6)


class OpenAIAgentAdapter(BaseAgentAdapter):
    """
    Real LLM provider adapter executing inferences via official OpenAI Python SDK.
    Captures:
    - Actual response text
    - Provider and model identifier
    - Measured round-trip latency (ms)
    - Measured actual token usage from provider (prompt + completion)
    - Calculated cost (USD) based on published pricing, or marked unavailable
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
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.OPENAI_BASE_URL
        self.timeout_seconds = timeout_seconds or settings.OPENAI_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.OPENAI_MAX_RETRIES
        self._client = client

    def _get_client(self) -> Any:
        """Lazily initialize and return OpenAI SDK client."""
        if self._client is not None:
            return self._client

        if not self.api_key:
            return None

        try:
            import os
            from openai import OpenAI
            if os.environ.get("OPENAI_BASE_URL") == "":
                os.environ.pop("OPENAI_BASE_URL", None)

            client_kwargs: Dict[str, Any] = {
                "api_key": self.api_key,
                "timeout": self.timeout_seconds,
                "max_retries": self.max_retries,
            }
            if self.base_url and self.base_url.strip():
                client_kwargs["base_url"] = self.base_url.strip()
            self._client = OpenAI(**client_kwargs)
            return self._client
        except Exception as exc:
            logger.error("Failed to initialize OpenAI client: %s", str(exc))
            return None

    def execute(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_name: Optional[str] = None,
        expected_output: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutionResult:
        resolved_model = model_name or settings.OPENAI_MODEL

        # 1. Credential Check
        if not self.api_key:
            logger.warning(
                "OpenAIAgentAdapter: OPENAI_API_KEY not configured. Failing case explicitly without mock fallback."
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
                error_message="OpenAI API key not configured. Set OPENAI_API_KEY environment variable to execute real provider evaluations.",
                cost_usd=None,
                model_name=resolved_model,
                model_provider="openai",
                raw_response={"error_type": "missing_api_key", "provider": "openai"},
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
                error_message="Failed to initialize OpenAI client library.",
                cost_usd=None,
                model_name=resolved_model,
                model_provider="openai",
                raw_response={"error_type": "client_initialization_failure", "provider": "openai"},
            )

        # 2. Build Messages Payload
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt})

        # 3. Execute Real API Call with High-Precision Wall-Clock Latency Measurement
        start_perf = time.perf_counter()
        try:
            import openai

            response = client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                timeout=self.timeout_seconds,
            )
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
                    model_provider="openai",
                    raw_response={"error_type": "empty_choices", "provider": "openai"},
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
                    model_provider="openai",
                    raw_response={"finish_reason": finish_reason, "provider": "openai"},
                )

            # 5. Extract Token Usage (Actual from Provider)
            usage = getattr(response, "usage", None)
            tokens_estimated = False
            if usage:
                prompt_tokens = getattr(usage, "prompt_tokens", None)
                completion_tokens = getattr(usage, "completion_tokens", None)
                total_tokens = getattr(usage, "total_tokens", None)
                if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
                    total_tokens = prompt_tokens + completion_tokens
            else:
                # If provider omitted usage, calculate fallback estimate explicitly flagged
                prompt_words = len(prompt.split()) if prompt else 1
                output_words = len(output_text.split()) if output_text else 1
                prompt_tokens = max(1, (prompt_words * 4) // 3)
                completion_tokens = max(1, (output_words * 4) // 3)
                total_tokens = prompt_tokens + completion_tokens
                tokens_estimated = True

            # 6. Calculate Reliable Cost (USD)
            cost_usd = calculate_openai_cost(
                model_name=resolved_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

            raw_meta = {
                "provider": "openai",
                "model": resolved_model,
                "response_id": getattr(response, "id", None),
                "finish_reason": finish_reason,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "tokens_estimated": tokens_estimated,
                "cost_usd": cost_usd,
            }

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
                model_provider="openai",
                raw_response=raw_meta,
            )

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_perf) * 1000.0, 2)
            import openai

            error_type = "unknown_error"
            if isinstance(exc, openai.AuthenticationError):
                error_type = "authentication_error"
                diag_msg = f"Invalid API credentials (AuthenticationError): {exc.message}"
            elif isinstance(exc, openai.RateLimitError):
                error_type = "rate_limit_error"
                diag_msg = f"Rate limit exceeded (RateLimitError): {exc.message}"
            elif isinstance(exc, openai.APITimeoutError):
                error_type = "timeout_error"
                diag_msg = f"Provider request timed out ({self.timeout_seconds}s limit reached)."
            elif isinstance(exc, openai.APIConnectionError):
                error_type = "connection_error"
                diag_msg = f"Network connection failure to OpenAI endpoint: {exc.message}"
            elif isinstance(exc, openai.BadRequestError):
                error_type = "bad_request"
                diag_msg = f"Bad request to model API: {exc.message}"
            elif isinstance(exc, openai.InternalServerError):
                error_type = "internal_server_error"
                diag_msg = f"OpenAI internal service error: {exc.message}"
            elif isinstance(exc, openai.APIError):
                error_type = "api_error"
                diag_msg = f"OpenAI API error: {exc.message}"
            else:
                diag_msg = f"Unexpected provider error: {str(exc)}"

            logger.error("OpenAIAgentAdapter execution failed for model %s: %s", resolved_model, diag_msg)

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
                model_provider="openai",
                raw_response={
                    "provider": "openai",
                    "model": resolved_model,
                    "error_type": error_type,
                    "exception_class": type(exc).__name__,
                },
            )
