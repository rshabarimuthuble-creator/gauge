import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import openai
from app.services.adapters.base import AgentExecutionResult
from app.services.adapters.openai_adapter import (
    OpenAIAgentAdapter,
    calculate_openai_cost,
    OPENAI_MODEL_PRICING,
)
from app.services.adapters.factory import get_agent_adapter
from app.services.adapters.mock_adapter import MockAgentAdapter
from app.models.agent_version import AgentVersion
from app.models.dataset import EvaluationDataset
from app.models.test_case import EvaluationTestCase


def test_calculate_openai_cost():
    # Known model: gpt-4o ($2.50 in, $10.00 out per 1M tokens)
    cost = calculate_openai_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)
    # 1000 * 2.50 / 1e6 + 500 * 10.00 / 1e6 = 0.0025 + 0.0050 = 0.0075
    assert cost == 0.0075

    # Known model: gpt-4o-mini ($0.15 in, $0.60 out per 1M tokens)
    mini_cost = calculate_openai_cost("gpt-4o-mini", prompt_tokens=10000, completion_tokens=10000)
    # 10000 * 0.15 / 1e6 + 10000 * 0.60 / 1e6 = 0.0015 + 0.0060 = 0.0075
    assert mini_cost == 0.0075

    # Unknown / custom model returns None (reliably marked unavailable)
    unknown_cost = calculate_openai_cost("custom-proprietary-model", prompt_tokens=500, completion_tokens=500)
    assert unknown_cost is None

    # Missing tokens returns None
    assert calculate_openai_cost("gpt-4o", prompt_tokens=None, completion_tokens=500) is None
    assert calculate_openai_cost("gpt-4o", prompt_tokens=100, completion_tokens=None) is None


def test_openai_adapter_missing_api_key():
    adapter = OpenAIAgentAdapter(api_key=None)
    with patch("app.core.config.settings.OPENAI_API_KEY", None):
        adapter.api_key = None
        result = adapter.execute(prompt="Hello")

    assert result.is_error is True
    assert result.is_mock is False
    assert result.output is None
    assert "OpenAI API key not configured" in (result.error_message or "")
    assert result.model_provider == "openai"


def test_openai_adapter_successful_execution():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "The capital of France is Paris."
    mock_choice.finish_reason = "stop"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 15
    mock_usage.completion_tokens = 8
    mock_usage.total_tokens = 23

    mock_response = MagicMock()
    mock_response.id = "chatcmpl-test-123"
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    mock_client.chat.completions.create.return_value = mock_response

    adapter = OpenAIAgentAdapter(api_key="sk-mock-key-for-unit-test", client=mock_client)
    result = adapter.execute(
        prompt="Capital of France?",
        system_prompt="You are a helpful geography assistant.",
        model_name="gpt-4o",
    )

    assert result.is_error is False
    assert result.is_mock is False
    assert result.tokens_estimated is False
    assert result.output == "The capital of France is Paris."
    assert result.token_usage == 23
    assert result.prompt_tokens == 15
    assert result.completion_tokens == 8
    assert result.cost_usd is not None
    assert result.cost_usd > 0
    assert result.latency_ms >= 0.0
    assert result.model_name == "gpt-4o"
    assert result.model_provider == "openai"
    assert result.raw_response["response_id"] == "chatcmpl-test-123"
    assert result.raw_response["finish_reason"] == "stop"


def test_openai_adapter_fallback_token_estimation_when_usage_missing():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Four."
    mock_choice.finish_reason = "stop"

    mock_response = MagicMock()
    mock_response.id = "chatcmpl-test-no-usage"
    mock_response.choices = [mock_choice]
    mock_response.usage = None  # Provider omitted usage

    mock_client.chat.completions.create.return_value = mock_response

    adapter = OpenAIAgentAdapter(api_key="sk-mock-key", client=mock_client)
    result = adapter.execute(prompt="What is 2 + 2?", model_name="gpt-4o")

    assert result.is_error is False
    assert result.is_mock is False
    assert result.tokens_estimated is True  # Explicitly flagged as estimated
    assert result.token_usage is not None
    assert result.token_usage > 0


def test_openai_adapter_authentication_error():
    mock_client = MagicMock()
    # Create fake request for OpenAI exception
    fake_request = MagicMock()
    mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
        message="Incorrect API key provided.",
        response=MagicMock(status_code=401, headers={}),
        body={"error": {"message": "Incorrect API key provided."}},
    )

    adapter = OpenAIAgentAdapter(api_key="sk-invalid-key", client=mock_client)
    result = adapter.execute(prompt="Hello")

    assert result.is_error is True
    assert result.is_mock is False  # Never falls back to mock
    assert result.output is None
    assert "AuthenticationError" in (result.error_message or "")
    assert result.raw_response["error_type"] == "authentication_error"


def test_openai_adapter_rate_limit_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = openai.RateLimitError(
        message="Rate limit reached for requests.",
        response=MagicMock(status_code=429, headers={}),
        body={"error": {"message": "Rate limit reached."}},
    )

    adapter = OpenAIAgentAdapter(api_key="sk-key", client=mock_client)
    result = adapter.execute(prompt="Heavy benchmark prompt")

    assert result.is_error is True
    assert result.is_mock is False
    assert "RateLimitError" in (result.error_message or "")
    assert result.raw_response["error_type"] == "rate_limit_error"


def test_openai_adapter_timeout_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = openai.APITimeoutError(
        request=MagicMock()
    )

    adapter = OpenAIAgentAdapter(api_key="sk-key", client=mock_client)
    result = adapter.execute(prompt="Timeout prompt")

    assert result.is_error is True
    assert result.is_mock is False
    assert "timed out" in (result.error_message or "").lower()
    assert result.raw_response["error_type"] == "timeout_error"


def test_openai_adapter_connection_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = openai.APIConnectionError(
        request=MagicMock(),
        message="Connection refused to api.openai.com",
    )

    adapter = OpenAIAgentAdapter(api_key="sk-key", client=mock_client)
    result = adapter.execute(prompt="Network test prompt")

    assert result.is_error is True
    assert result.is_mock is False
    assert "connection" in (result.error_message or "").lower()


def test_openai_adapter_empty_and_malformed_response():
    mock_client = MagicMock()
    # 1. Empty choices
    mock_client.chat.completions.create.return_value = MagicMock(choices=[])
    adapter = OpenAIAgentAdapter(api_key="sk-key", client=mock_client)
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


def test_adapter_factory_resolution():
    # 1. Explicit mock mode
    mock_adapter = get_agent_adapter(provider="openai", execution_mode="mock")
    assert isinstance(mock_adapter, MockAgentAdapter)

    # 2. Explicit real mode
    real_adapter = get_agent_adapter(provider="openai", execution_mode="real")
    assert isinstance(real_adapter, OpenAIAgentAdapter)

    # 3. Explicit provider mock
    provider_mock = get_agent_adapter(provider="mock")
    assert isinstance(provider_mock, MockAgentAdapter)

    # 4. Unsupported provider in real mode raises ValueError
    with pytest.raises(ValueError, match="Unsupported real LLM provider"):
        get_agent_adapter(provider="unsupported_provider", execution_mode="real")


def test_full_evaluation_flow_with_real_adapter(client: TestClient, db_session: Session):
    """
    Validates end-to-end evaluation execution via FastAPI route with execution_mode='real'
    and mocked OpenAI SDK client.
    """
    # 1. Create dataset and test cases
    dataset = EvaluationDataset(name="Live Q&A Benchmark", description="Test suite for real adapter")
    db_session.add(dataset)
    db_session.flush()

    tc1 = EvaluationTestCase(
        dataset_id=dataset.id,
        case_identifier="tc-live-1",
        input_prompt="What is the speed of light?",
        expected_output="299,792,458 m/s",
    )
    tc2 = EvaluationTestCase(
        dataset_id=dataset.id,
        case_identifier="tc-live-2",
        input_prompt="What is 10 + 10?",
        expected_output="20",
    )
    db_session.add_all([tc1, tc2])

    agent = AgentVersion(
        name="GPT-4o Production Agent",
        version="v2.0.0",
        model_provider="openai",
        model_name="gpt-4o",
        prompt_text="Answer accurately.",
    )
    db_session.add(agent)
    db_session.commit()

    # 2. Mock OpenAI chat completion responses
    mock_choice1 = MagicMock()
    mock_choice1.message.content = "299,792,458 m/s"
    mock_choice1.finish_reason = "stop"
    mock_usage1 = MagicMock(prompt_tokens=10, completion_tokens=8, total_tokens=18)
    resp1 = MagicMock(id="cmpl-1", choices=[mock_choice1], usage=mock_usage1)

    mock_choice2 = MagicMock()
    mock_choice2.message.content = "20"
    mock_choice2.finish_reason = "stop"
    mock_usage2 = MagicMock(prompt_tokens=6, completion_tokens=2, total_tokens=8)
    resp2 = MagicMock(id="cmpl-2", choices=[mock_choice2], usage=mock_usage2)

    with patch("app.core.config.settings.OPENAI_API_KEY", "sk-mock-unit-test-key"), patch.object(OpenAIAgentAdapter, "_get_client") as mock_get_client:
        mock_sdk = MagicMock()
        mock_sdk.chat.completions.create.side_effect = [resp1, resp2]
        mock_get_client.return_value = mock_sdk

        # Trigger run with explicit execution_mode='real'
        payload = {
            "name": "Live Real Provider Evaluation Run",
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
            assert r["is_mock"] is False  # Proves execution was real
            assert r["tokens_estimated"] is False  # Actual tokens from provider
            assert r["token_usage"] > 0
            assert r["latency_ms"] >= 0.0

            # Verify persisted metadata_json contains provider, model, tokens, and cost
            meta = json.loads(r["metadata_json"])
            assert meta["provider"] == "openai"
            assert meta["model"] == "gpt-4o"
            assert meta["prompt_tokens"] in (10, 6)
            assert meta["completion_tokens"] in (8, 2)
            assert "cost_usd" in meta


def test_full_evaluation_flow_real_provider_error_handling(client: TestClient, db_session: Session):
    """
    Validates that when a real provider call fails (e.g. rate limit),
    it is recorded as an 'error' and NOT converted to a passing score or mock fallback.
    """
    dataset = EvaluationDataset(name="Error Benchmark")
    db_session.add(dataset)
    db_session.flush()

    tc = EvaluationTestCase(
        dataset_id=dataset.id,
        case_identifier="tc-err-1",
        input_prompt="Trigger rate limit",
        expected_output="Expected answer",
    )
    db_session.add(tc)

    agent = AgentVersion(
        name="Agent Error Test",
        version="v1.0.0",
        model_provider="openai",
        model_name="gpt-4o",
    )
    db_session.add(agent)
    db_session.commit()

    with patch("app.core.config.settings.OPENAI_API_KEY", "sk-mock-unit-test-key"), patch.object(OpenAIAgentAdapter, "_get_client") as mock_get_client:
        mock_sdk = MagicMock()
        mock_sdk.chat.completions.create.side_effect = openai.RateLimitError(
            message="429 Rate Limit Exceeded",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "Rate limit exceeded"}},
        )
        mock_get_client.return_value = mock_sdk

        payload = {
            "name": "Rate Limited Evaluation Run",
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
        assert data["pass_rate"] is None  # Errored case excluded from eligible denominator

        result = data["results"][0]
        assert result["status"] == "error"
        assert result["is_mock"] is False  # Never falls back to mock
        assert "RateLimitError" in result["error_message"]
