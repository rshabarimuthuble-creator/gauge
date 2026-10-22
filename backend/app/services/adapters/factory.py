from typing import Optional
from app.services.adapters.base import BaseAgentAdapter
from app.services.adapters.mock_adapter import MockAgentAdapter
from app.services.adapters.openai_adapter import OpenAIAgentAdapter
from app.services.adapters.groq_adapter import GroqAgentAdapter
from app.core.config import settings
from app.core.logging import logger


def get_agent_adapter(
    provider: Optional[str] = None,
    simulated_delay_ms: float = 5.0,
    execution_mode: Optional[str] = None,
) -> BaseAgentAdapter:
    """
    Returns an agent adapter instance based on provider name and requested execution mode.

    Modes:
    - 'mock': Explicitly routes to MockAgentAdapter for deterministic local zero-key evaluation.
    - 'real': Explicitly routes to a real LLM provider (GroqAgentAdapter or OpenAIAgentAdapter). Never falls back to mock.
    - 'auto' / None:
        - If provider is explicitly 'mock', returns MockAgentAdapter.
        - In 'testing' environment without explicit real mode, preserves MockAgentAdapter for zero-key tests.
        - In development/production with API keys present:
            - If provider is 'groq' (or settings.LLM_PROVIDER is 'groq') and GROQ_API_KEY is configured: routes to GroqAgentAdapter.
            - If provider is 'openai' and OPENAI_API_KEY is configured: routes to OpenAIAgentAdapter.
            - Otherwise defaults to MockAgentAdapter.
    """
    target_provider = (provider or settings.LLM_PROVIDER).strip().lower()
    mode = (execution_mode or settings.DEFAULT_EXECUTION_MODE).strip().lower()

    logger.debug(
        "Resolving agent adapter: provider='%s', mode='%s', env='%s'",
        target_provider,
        mode,
        settings.ENVIRONMENT,
    )

    # 0. In testing environment without explicit execution_mode, preserve MockAgentAdapter for zero-key test suite
    if execution_mode is None and settings.ENVIRONMENT == "testing":
        return MockAgentAdapter(simulated_delay_ms=simulated_delay_ms)

    # 1. Explicit Mock Execution
    if mode == "mock" or target_provider in ("mock", "mock-adapter", "mock_adapter"):
        return MockAgentAdapter(simulated_delay_ms=simulated_delay_ms)

    # 2. Explicit Real Provider Execution
    if mode == "real":
        if target_provider == "groq":
            return GroqAgentAdapter()
        elif target_provider == "openai":
            return OpenAIAgentAdapter()
        else:
            raise ValueError(
                f"Unsupported real LLM provider '{target_provider}'. Currently supported real providers: 'groq', 'openai'."
            )

    # 3. Auto Mode Resolution
    # In testing environment without explicit 'real' mode, preserve mock adapter for zero-key test suite
    if settings.ENVIRONMENT == "testing":
        return MockAgentAdapter(simulated_delay_ms=simulated_delay_ms)

    if target_provider == "groq":
        if settings.GROQ_API_KEY:
            return GroqAgentAdapter()
        else:
            logger.info("Groq provider selected but GROQ_API_KEY unset; defaulting to MockAgentAdapter.")
            return MockAgentAdapter(simulated_delay_ms=simulated_delay_ms)

    if target_provider == "openai":
        if settings.OPENAI_API_KEY:
            return OpenAIAgentAdapter()
        else:
            logger.info("OpenAI provider selected but OPENAI_API_KEY unset; defaulting to MockAgentAdapter.")
            return MockAgentAdapter(simulated_delay_ms=simulated_delay_ms)

    # If general provider is configured as groq in settings
    if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
        return GroqAgentAdapter()
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return OpenAIAgentAdapter()

    return MockAgentAdapter(simulated_delay_ms=simulated_delay_ms)
