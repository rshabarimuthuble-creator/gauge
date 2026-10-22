import time
from typing import Optional, Dict, Any
from app.services.adapters.base import BaseAgentAdapter, AgentExecutionResult
from app.core.logging import logger


class MockAgentAdapter(BaseAgentAdapter):
    """
    Deterministic mock adapter for Day 2 agent evaluation testing.
    Produces predictable responses, measures real wall-clock latency, deterministically
    estimates token counts, and clearly flags all responses as mock data.
    """

    def __init__(self, simulated_delay_ms: float = 5.0):
        self.simulated_delay_ms = simulated_delay_ms

    def execute(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_name: Optional[str] = None,
        expected_output: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutionResult:
        meta = metadata or {}
        start_perf = time.perf_counter()

        # Simulate small execution overhead
        if self.simulated_delay_ms > 0:
            time.sleep(self.simulated_delay_ms / 1000.0)

        # 1. Error simulation check
        if (
            "__SIMULATE_ERROR__" in prompt
            or "[SIMULATE_ERROR]" in prompt
            or meta.get("simulate") == "error"
            or meta.get("simulate_error") is True
        ):
            latency_ms = round((time.perf_counter() - start_perf) * 1000.0, 2)
            custom_error = meta.get("error_message") or "Simulated agent execution error: remote model endpoint unreachable."
            logger.info("MockAgentAdapter: simulated error triggered for prompt '%s'", prompt[:30])
            return AgentExecutionResult(
                output=None,
                latency_ms=latency_ms,
                token_usage=0,
                prompt_tokens=0,
                completion_tokens=0,
                tokens_estimated=True,
                is_mock=True,
                is_error=True,
                error_message=custom_error,
                raw_response={"simulation": "error", "model": model_name or "mock-model"},
            )

        # 2. Explicit canned / mock response check
        if meta.get("mock_response"):
            output = str(meta["mock_response"])
        elif (
            "__SIMULATE_INCORRECT__" in prompt
            or "[SIMULATE_INCORRECT]" in prompt
            or meta.get("simulate") == "incorrect"
            or meta.get("simulate_incorrect") is True
        ):
            # Output guaranteed to differ from expected_output
            output = f"[Mock Agent] Deliberately incorrect answer for: {prompt[:30]}"
            if expected_output and output.strip() == expected_output.strip():
                output = output + "_variant_incorrect"
        elif (
            "__SIMULATE_CORRECT__" in prompt
            or "[SIMULATE_CORRECT]" in prompt
            or meta.get("simulate") == "correct"
            or meta.get("simulate_correct") is True
        ):
            output = expected_output if expected_output is not None else f"[Mock Agent] Correct answer for: {prompt[:30]}"
        elif expected_output is not None:
            # Default behavior when expected output is present: deterministic match
            output = expected_output
        else:
            # Default behavior when no expected output: informative mock output
            output = f"[Mock Agent Output] Evaluated response for prompt: '{prompt.strip()[:50]}'"

        latency_ms = round((time.perf_counter() - start_perf) * 1000.0, 2)

        # Deterministic token estimation (explicitly flagged as estimated)
        prompt_words = len(prompt.split()) if prompt else 1
        output_words = len(output.split()) if output else 1
        prompt_tokens = max(1, (prompt_words * 4) // 3)
        completion_tokens = max(1, (output_words * 4) // 3)
        token_usage = prompt_tokens + completion_tokens

        return AgentExecutionResult(
            output=output,
            latency_ms=latency_ms,
            token_usage=token_usage,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tokens_estimated=True,
            is_mock=True,
            is_error=False,
            error_message=None,
            raw_response={
                "simulation": "mock",
                "model": model_name or "mock-model",
                "adapter": "MockAgentAdapter",
            },
        )
