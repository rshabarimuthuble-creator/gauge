import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sqlalchemy import text
from app.models.dataset import EvaluationDataset
from app.models.agent_version import AgentVersion
from app.models.test_case import EvaluationTestCase
from app.models.evaluation_run import EvaluationRun
from app.models.evaluation_result import EvaluationResult
from app.services.adapters.groq_adapter import GroqAgentAdapter


@pytest.fixture(autouse=True)
def clean_db_after_test(db_session: Session):
    yield
    conn = db_session.get_bind()
    conn.execute(text("DELETE FROM evaluation_results"))
    conn.execute(text("DELETE FROM evaluation_runs"))
    conn.execute(text("DELETE FROM evaluation_test_cases"))
    conn.execute(text("DELETE FROM evaluation_datasets"))
    conn.execute(text("DELETE FROM agent_versions"))
    conn.commit()





def create_test_dataset(db: Session, name="Timeout Benchmark") -> EvaluationDataset:
    dataset = EvaluationDataset(
        name=name,
        description="Dataset for testing launch timeout and background execution",
    )
    db.add(dataset)
    db.flush()

    for i in range(1, 4):
        tc = EvaluationTestCase(
            dataset_id=dataset.id,
            case_identifier=f"case-{i}",
            input_prompt=f"Prompt {i}",
            expected_output=f"Output {i}",
        )
        db.add(tc)

    db.commit()
    db.refresh(dataset)
    return dataset


def create_test_agent(db: Session, name="Timeout Test Agent") -> AgentVersion:
    agent = AgentVersion(
        name=name,
        version="v1.0.0",
        model_provider="mock",
        model_name="mock-model",
        prompt_text="You are a mock test agent.",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def test_default_sync_launch_backward_compatibility(client: TestClient, db_session: Session):
    """
    Default POST /api/v1/evaluations (background=False) executes synchronously,
    returning HTTP 201 with status='completed' and all results for test suite compatibility.
    """
    dataset = create_test_dataset(db_session, "Sync DS")
    agent = create_test_agent(db_session, "Sync Agent")

    response = client.post("/api/v1/evaluations", json={
        "name": "Sync Launch Run",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
        "execution_mode": "mock",
    })

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert data["total_cases"] == 3
    assert data["passed_cases"] == 3
    assert len(data["results"]) == 3


def test_background_launch_returns_running_status_immediately(client: TestClient, db_session: Session):
    """
    POST /api/v1/evaluations with background=True returns HTTP 201 immediately with
    status='running', and polling GET /api/v1/evaluations/{id} observes completion.
    """
    dataset = create_test_dataset(db_session, "Async DS")
    agent = create_test_agent(db_session, "Async Agent")

    response = client.post("/api/v1/evaluations?background=true", json={
        "name": "Async Launch Run",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
        "execution_mode": "mock",
    })

    assert response.status_code == 201
    data = response.json()
    run_id = data["id"]
    # Initial response is in 'running' state
    assert data["status"] in ("running", "completed")

    # Poll until background thread finishes execution (timeout at 10s)
    completed_data = None
    for _ in range(50):
        poll_res = client.get(f"/api/v1/evaluations/{run_id}")
        assert poll_res.status_code == 200
        poll_json = poll_res.json()
        if poll_json["status"] in ("completed", "failed"):
            completed_data = poll_json
            break
        time.sleep(0.1)

    assert completed_data is not None
    assert completed_data["status"] == "completed"
    assert completed_data["total_cases"] == 3
    assert completed_data["passed_cases"] == 3


def test_prevent_accidental_duplicate_evaluation_launch(client: TestClient, db_session: Session):
    """
    If an evaluation run for (dataset_id, agent_version_id) is currently 'running',
    a duplicate launch request is rejected with HTTP 409 Conflict.
    """
    dataset = create_test_dataset(db_session, "Duplicate Check DS")
    agent = create_test_agent(db_session, "Duplicate Check Agent")

    # Manually create an in-flight 'running' evaluation started 1 minute ago
    active_run = EvaluationRun(
        name="Active In-Flight Run",
        dataset_id=dataset.id,
        agent_version_id=agent.id,
        status="running",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        dataset_version=dataset.version,
    )
    db_session.add(active_run)
    db_session.commit()

    # Attempt to launch duplicate evaluation
    response = client.post("/api/v1/evaluations", json={
        "name": "Duplicate Attempt",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
        "execution_mode": "mock",
    })

    assert response.status_code == 409
    assert "already running" in response.json()["detail"]
    assert active_run.id in response.json()["detail"]


def test_stale_running_evaluation_auto_expires_and_allows_new_run(client: TestClient, db_session: Session):
    """
    If an evaluation run was left 'running' older than 15 minutes (e.g. server crash),
    it is auto-expired to 'failed' and does not block a new run.
    """
    dataset = create_test_dataset(db_session, "Stale DS")
    agent = create_test_agent(db_session, "Stale Agent")

    stale_run = EvaluationRun(
        name="Stale Interrupted Run",
        dataset_id=dataset.id,
        agent_version_id=agent.id,
        status="running",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=25),
        dataset_version=dataset.version,
    )
    db_session.add(stale_run)
    db_session.commit()
    stale_run_id = stale_run.id

    # Launch new evaluation - should succeed because previous is stale (>15m)
    response = client.post("/api/v1/evaluations", json={
        "name": "Fresh Replacement Run",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
        "execution_mode": "mock",
    })

    assert response.status_code == 201
    assert response.json()["status"] == "completed"

    # Verify stale run was marked as failed
    db_session.expire_all()
    refreshed_stale = db_session.get(EvaluationRun, stale_run_id)
    assert refreshed_stale.status == "failed"
    assert "timed out or was interrupted" in refreshed_stale.error_message


def test_groq_retry_guidance_header_and_message_extraction():
    """
    Unit test extraction of rate-limit guidance seconds from provider response headers
    and exception text.
    """
    class MockResponseWithHeaders:
        def __init__(self, headers):
            self.headers = headers

    class MockRateLimitError(Exception):
        def __init__(self, message, headers=None):
            super().__init__(message)
            self.message = message
            self.response = MockResponseWithHeaders(headers) if headers else None

    # 1. 'retry-after' header
    exc1 = MockRateLimitError("Rate limit", headers={"retry-after": "4.2"})
    assert GroqAgentAdapter._extract_retry_guidance(exc1) == 4.2

    # 2. 'x-ratelimit-reset-requests' in ms
    exc2 = MockRateLimitError("Rate limit", headers={"x-ratelimit-reset-requests": "1500ms"})
    assert GroqAgentAdapter._extract_retry_guidance(exc2) == 1.5

    # 3. 'x-ratelimit-reset-tokens' in s
    exc3 = MockRateLimitError("Rate limit", headers={"x-ratelimit-reset-tokens": "3.5s"})
    assert GroqAgentAdapter._extract_retry_guidance(exc3) == 3.5

    # 4. Fallback text parsing from exception message: 'try again in 2.5s'
    exc4 = MockRateLimitError("Please try again in 2.5s.")
    assert GroqAgentAdapter._extract_retry_guidance(exc4) == 2.5

    # 5. Fallback text parsing in ms: 'try again in 500ms'
    exc5 = MockRateLimitError("Please try again in 500ms.")
    assert GroqAgentAdapter._extract_retry_guidance(exc5) == 0.5

    # 6. No rate limit guidance available
    exc6 = MockRateLimitError("Generic 429 message without timing")
    assert GroqAgentAdapter._extract_retry_guidance(exc6) is None


def test_groq_adapter_bounded_retries_on_rate_limit():
    """
    Verify GroqAgentAdapter executes bounded retries (max_attempts = 3) on RateLimitError,
    sleeps according to extracted guidance, and does not loop indefinitely.
    """
    import groq

    adapter = GroqAgentAdapter(api_key="gsk-test-key-mock")
    mock_client = MagicMock()

    # Raise RateLimitError on every call
    mock_response = MagicMock()
    mock_response.headers = {"retry-after": "1.0"}
    rle = groq.RateLimitError(
        message="Rate limit reached: try again in 1.0s",
        response=mock_response,
        body={},
    )
    mock_client.chat.completions.create.side_effect = rle
    adapter._client = mock_client

    with patch("time.sleep") as mock_sleep:
        result = adapter.execute(prompt="Hello")

    # Should have attempted 3 times, sleeping between attempt 1->2 and 2->3
    assert mock_client.chat.completions.create.call_count == 3
    assert mock_sleep.call_count == 2
    assert result.is_error is True
    assert "rate limit" in result.error_message.lower()
    assert result.raw_response["error_type"] == "rate_limit_error"
