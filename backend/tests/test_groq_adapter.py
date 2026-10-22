import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import groq
from app.services.adapters.base import AgentExecutionResult
from app.services.adapters.groq_adapter import (
    GroqAgentAdapter,
    calculate_groq_cost,
    GROQ_MODEL_PRICING,
)
from app.services.adapters.factory import get_agent_adapter
from app.services.adapters.mock_adapter import MockAgentAdapter
from app.services.adapters.openai_adapter import OpenAIAgentAdapter
from app.models.agent_version import AgentVersion
from app.models.dataset import EvaluationDataset
from app.models.test_case import EvaluationTestCase


def test_calculate_groq_cost():
    # Known model: llama-3.3-70b-versatile ($0.59 in, $0.79 out per 1M tokens)
    cost = calculate_groq_cost("llama-3.3-70b-versatile", prompt_tokens=1000, completion_tokens=500)
    # 1000 * 0.59 / 1e6 + 500 * 0.79 / 1e6 = 0.00059 + 0.000395 = 0.000985
    assert cost == pytest.approx(0.000985, rel=1e-5)

    # Known model: llama-3.1-8b-instant ($0.05 in, $0.08 out per 1M tokens)
    mini_cost = calculate_groq_cost("llama-3.1-8b-instant", prompt_tokens=10000, completion_tokens=10000)
    # 10000 * 0.05 / 1e6 + 10000 * 0.08 / 1e6 = 0.0005 + 0.0008 = 0.0013
    assert mini_cost == pytest.approx(0.0013, rel=1e-5)

    # Unknown / preview model returns None (accurately labeled unavailable)
    unknown_cost = calculate_groq_cost("openai/gpt-oss-20b", prompt_tokens=500, completion_tokens=500)
    assert unknown_cost is None

    # Missing tokens returns None
    assert calculate_groq_cost("llama-3.3-70b-versatile", prompt_tokens=None, completion_tokens=500) is None
    assert calculate_groq_cost("llama-3.3-70b-versatile", prompt_tokens=100, completion_tokens=None) is None


def test_groq_adapter_missing_api_key():
    adapter = GroqAgentAdapter(api_key=None)
    with patch("app.core.config.settings.GROQ_API_KEY", None):
        adapter.api_key = None
        result = adapter.execute(prompt="Hello")

    assert result.is_error is True
    assert result.is_mock is False
    assert result.output is None
    assert "Groq API key not configured" in (result.error_message or "")
    assert result.model_provider == "groq"


def test_groq_adapter_successful_execution():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Groq is an AI infrastructure company."
    mock_choice.finish_reason = "stop"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 12
    mock_usage.completion_tokens = 9
    mock_usage.total_tokens = 21
    mock_usage.completion_time = 0.015
    mock_usage.prompt_time = 0.004
    mock_usage.queue_time = 0.001
    mock_usage.total_time = 0.020

    mock_response = MagicMock()
    mock_response.id = "chatcmpl-groq-test-123"
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    mock_client.chat.completions.create.return_value = mock_response

    adapter = GroqAgentAdapter(api_key="gsk_mock_test_key_for_unit_tests", client=mock_client)
    result = adapter.execute(
        prompt="Explain Groq briefly.",
        system_prompt="You are a helpful technology assistant.",
        model_name="openai/gpt-oss-20b",
    )

    assert result.is_error is False
    assert result.is_mock is False
    assert result.tokens_estimated is False
    assert result.output == "Groq is an AI infrastructure company."
    assert result.token_usage == 21
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 9
    assert result.latency_ms >= 0.0
    assert result.model_name == "openai/gpt-oss-20b"
    assert result.model_provider == "groq"
    assert result.raw_response["response_id"] == "chatcmpl-groq-test-123"
    assert result.raw_response["finish_reason"] == "stop"
    assert result.raw_response["groq_timings"]["completion_time"] == 0.015


def test_groq_adapter_fallback_token_estimation_when_usage_missing():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Paris is the capital."
    mock_choice.finish_reason = "stop"

    mock_response = MagicMock()
    mock_response.id = "chatcmpl-groq-no-usage"
    mock_response.choices = [mock_choice]
    mock_response.usage = None  # Provider omitted usage

    mock_client.chat.completions.create.return_value = mock_response

    adapter = GroqAgentAdapter(api_key="gsk_mock_key", client=mock_client)
    result = adapter.execute(prompt="Capital of France?", model_name="openai/gpt-oss-20b")

    assert result.is_error is False
    assert result.is_mock is False
    assert result.tokens_estimated is True
    assert result.token_usage is not None
    assert result.token_usage > 0


def test_groq_adapter_authentication_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = groq.AuthenticationError(
        message="Invalid Groq API Key.",
        response=MagicMock(status_code=401, headers={}),
        body={"error": {"message": "Invalid Groq API Key."}},
    )

    adapter = GroqAgentAdapter(api_key="gsk_invalid_key", client=mock_client)
    result = adapter.execute(prompt="Hello")

    assert result.is_error is True
    assert result.is_mock is False  # Never falls back to mock
    assert result.output is None
    assert "AuthenticationError" in (result.error_message or "")
    assert result.raw_response["error_type"] == "authentication_error"


def test_groq_adapter_rate_limit_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = groq.RateLimitError(
        message="Rate limit reached for requests per minute (TPM).",
        response=MagicMock(status_code=429, headers={}),
        body={"error": {"message": "Rate limit reached."}},
    )

    adapter = GroqAgentAdapter(api_key="gsk_key", client=mock_client)
    result = adapter.execute(prompt="Heavy benchmark prompt")

    assert result.is_error is True
    assert result.is_mock is False
    assert "RateLimitError" in (result.error_message or "")
    assert result.raw_response["error_type"] == "rate_limit_error"


def test_groq_adapter_timeout_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = groq.APITimeoutError(
        request=MagicMock()
    )

    adapter = GroqAgentAdapter(api_key="gsk_key", client=mock_client)
    result = adapter.execute(prompt="Timeout prompt")

    assert result.is_error is True
    assert result.is_mock is False
    assert "timed out" in (result.error_message or "").lower()
    assert result.raw_response["error_type"] == "timeout_error"


def test_groq_adapter_connection_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = groq.APIConnectionError(
        request=MagicMock(),
        message="Connection refused to api.groq.com",
    )

    adapter = GroqAgentAdapter(api_key="gsk_key", client=mock_client)
    result = adapter.execute(prompt="Network test prompt")

    assert result.is_error is True
    assert result.is_mock is False
    assert "connection" in (result.error_message or "").lower()
    assert result.raw_response["error_type"] == "connection_error"


def test_groq_adapter_empty_and_malformed_response():
    mock_client = MagicMock()
    # 1. Empty choices
    mock_client.chat.completions.create.return_value = MagicMock(choices=[])
    adapter = GroqAgentAdapter(api_key="gsk_key", client=mock_client)
    res_empty_choices = adapter.execute(prompt="Empty test")
    assert res_empty_choices.is_error is True
    assert "empty" in (res_empty_choices.error_message or "").lower()

    # 2. Content is empty string
    mock_choice = MagicMock()
    mock_choice.message.content = "   "
    mock_choice.finish_reason = "stop"
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice], usage=None)
    res_empty_content = adapter.execute(prompt="Empty content test")
    assert res_empty_content.is_error is True
    assert "empty" in (res_empty_content.error_message or "").lower()


def test_groq_adapter_factory_resolution():
    # 1. Explicit mock mode with groq provider
    mock_adapter = get_agent_adapter(provider="groq", execution_mode="mock")
    assert isinstance(mock_adapter, MockAgentAdapter)

    # 2. Explicit real mode with groq provider
    real_adapter = get_agent_adapter(provider="groq", execution_mode="real")
    assert isinstance(real_adapter, GroqAgentAdapter)

    # 3. Explicit real mode with openai provider (preserves Day 1 OpenAI functionality)
    openai_adapter = get_agent_adapter(provider="openai", execution_mode="real")
    assert isinstance(openai_adapter, OpenAIAgentAdapter)

    # 4. Default provider resolution when LLM_PROVIDER="groq"
    with patch("app.core.config.settings.LLM_PROVIDER", "groq"):
        default_real = get_agent_adapter(execution_mode="real")
        assert isinstance(default_real, GroqAgentAdapter)


def test_full_evaluation_flow_with_groq_adapter(client: TestClient, db_session: Session):
    """
    Validates end-to-end evaluation execution via FastAPI route with execution_mode='real'
    and mocked Groq SDK client.
    """
    # 1. Create dataset and test cases
    dataset = EvaluationDataset(name="Groq Speed Benchmark", description="Test suite for Groq adapter")
    db_session.add(dataset)
    db_session.flush()

    tc1 = EvaluationTestCase(
        dataset_id=dataset.id,
        case_identifier="tc-groq-1",
        input_prompt="What is 5 x 5?",
        expected_output="25",
    )
    tc2 = EvaluationTestCase(
        dataset_id=dataset.id,
        case_identifier="tc-groq-2",
        input_prompt="Name the red planet.",
        expected_output="Mars",
    )
    db_session.add_all([tc1, tc2])

    agent = AgentVersion(
        name="Groq Ultra-Fast Agent",
        version="v1.0.0",
        model_provider="groq",
        model_name="openai/gpt-oss-20b",
        prompt_text="Answer concisely.",
    )
    db_session.add(agent)
    db_session.commit()

    # 2. Mock Groq chat completion responses
    mock_choice1 = MagicMock()
    mock_choice1.message.content = "25"
    mock_choice1.finish_reason = "stop"
    mock_usage1 = MagicMock(
        prompt_tokens=8,
        completion_tokens=2,
        total_tokens=10,
        completion_time=0.008,
        prompt_time=0.002,
        queue_time=0.001,
        total_time=0.011,
    )
    resp1 = MagicMock(id="groq-cmpl-1", choices=[mock_choice1], usage=mock_usage1)

    mock_choice2 = MagicMock()
    mock_choice2.message.content = "Mars"
    mock_choice2.finish_reason = "stop"
    mock_usage2 = MagicMock(
        prompt_tokens=9,
        completion_tokens=2,
        total_tokens=11,
        completion_time=0.007,
        prompt_time=0.002,
        queue_time=0.001,
        total_time=0.010,
    )
    resp2 = MagicMock(id="groq-cmpl-2", choices=[mock_choice2], usage=mock_usage2)

    with patch("app.core.config.settings.GROQ_API_KEY", "gsk_test_mock_key"), patch.object(GroqAgentAdapter, "_get_client") as mock_get_client:
        mock_sdk = MagicMock()
        mock_sdk.chat.completions.create.side_effect = [resp1, resp2]
        mock_get_client.return_value = mock_sdk

        # Trigger run with explicit execution_mode='real'
        payload = {
            "name": "Live Groq Evaluation Run",
            "dataset_id": dataset.id,
            "agent_version_id": agent.id,
            "execution_mode": "real",
        }
        res = client.post("/api/v1/evaluations", json=payload)
        assert res.status_code == 201
        data = res.json()

        assert data["status"] == "completed"
        assert data["total_cases"] == 2
        assert data["passed_cases"] == 2
        assert data["failed_cases"] == 0
        assert data["errored_cases"] == 0
        assert data["pass_rate"] == 100.0

        # Verify case-level details
        results = data["results"]
        assert len(results) == 2
        for r in results:
            assert r["status"] == "passed"
            assert r["is_mock"] is False  # Proves execution was real Groq
            assert r["tokens_estimated"] is False  # Actual tokens from provider
            assert r["token_usage"] > 0
            assert r["latency_ms"] >= 0.0

            # Verify persisted metadata_json contains groq provider, model, tokens, and hardware timings
            meta = json.loads(r["metadata_json"])
            assert meta["provider"] == "groq"
            assert meta["model"] == "openai/gpt-oss-20b"
            assert meta["prompt_tokens"] in (8, 9)
            assert meta["completion_tokens"] == 2
            assert "groq_timings" in meta
            assert meta["groq_timings"]["completion_time"] in (0.008, 0.007)


def test_full_evaluation_flow_groq_error_handling(client: TestClient, db_session: Session):
    """
    Validates that when a Groq call fails (e.g. rate limit),
    it is recorded as an 'error' and NOT converted to a passing score or mock fallback.
    """
    dataset = EvaluationDataset(name="Groq Error Benchmark")
    db_session.add(dataset)
    db_session.flush()

    tc = EvaluationTestCase(
        dataset_id=dataset.id,
        case_identifier="tc-groq-err-1",
        input_prompt="Trigger Groq 429",
        expected_output="Expected answer",
    )
    db_session.add(tc)

    agent = AgentVersion(
        name="Groq Error Agent",
        version="v1.0.0",
        model_provider="groq",
        model_name="openai/gpt-oss-20b",
    )
    db_session.add(agent)
    db_session.commit()

    with patch("app.core.config.settings.GROQ_API_KEY", "gsk_test_mock_key"), patch.object(GroqAgentAdapter, "_get_client") as mock_get_client:
        mock_sdk = MagicMock()
        mock_sdk.chat.completions.create.side_effect = groq.RateLimitError(
            message="429 Groq Rate Limit Exceeded",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "Rate limit exceeded"}},
        )
        mock_get_client.return_value = mock_sdk

        payload = {
            "name": "Groq Rate Limited Evaluation Run",
            "dataset_id": dataset.id,
            "agent_version_id": agent.id,
            "execution_mode": "real",
        }
        res = client.post("/api/v1/evaluations", json=payload)
        assert res.status_code == 201
        data = res.json()

        assert data["status"] == "completed"
        assert data["total_cases"] == 1
        assert data["passed_cases"] == 0
        assert data["failed_cases"] == 0
        assert data["errored_cases"] == 1
        assert data["pass_rate"] is None

        result = data["results"][0]
        assert result["status"] == "error"
        assert result["is_mock"] is False  # Never falls back to mock
        assert "RateLimitError" in result["error_message"]
