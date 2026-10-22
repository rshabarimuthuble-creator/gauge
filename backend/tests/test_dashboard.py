from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.dataset import EvaluationDataset
from app.models.agent_version import AgentVersion
from app.models.evaluation_run import EvaluationRun


def test_dashboard_summary_empty_state(client: TestClient):
    """Test dashboard summary returns zero counts and expected structure when empty."""
    with patch("app.services.dashboard_service.check_db_connectivity", return_value=(True, "Connected")):
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["datasets_count"] == 0
        assert data["versions_count"] == 0
        assert data["total_runs_count"] == 0
        assert data["latest_run_status"] is None
        assert data["database_connected"] is True
        assert isinstance(data["recent_runs"], list)
        assert len(data["recent_runs"]) == 0


def test_dashboard_summary_with_records(client: TestClient, db_session: Session):
    """Test dashboard summary computes accurate counts when records exist."""
    # Seed a dataset
    dataset = EvaluationDataset(name="Customer Support Q&A", description="Support test cases")
    db_session.add(dataset)
    db_session.flush()

    # Seed an agent version
    agent = AgentVersion(
        name="Support Agent",
        version="v1.0.0",
        model_provider="openai",
        model_name="gpt-4o",
        prompt_text="You are a helpful customer support agent.",
    )
    db_session.add(agent)
    db_session.flush()

    # Seed an evaluation run
    run = EvaluationRun(
        name="Nightly Benchmark #1",
        status="completed",
        dataset_id=dataset.id,
        agent_version_id=agent.id,
    )
    db_session.add(run)
    db_session.commit()

    with patch("app.services.dashboard_service.check_db_connectivity", return_value=(True, "Connected")):
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["datasets_count"] == 1
        assert data["versions_count"] == 1
        assert data["total_runs_count"] == 1
        assert data["latest_run_status"] == "completed"
        assert len(data["recent_runs"]) == 1
        assert data["recent_runs"][0]["name"] == "Nightly Benchmark #1"


def test_dashboard_summary_when_db_down(client: TestClient):
    """Test dashboard summary handles DB offline status gracefully without throwing 500."""
    with patch("app.services.dashboard_service.check_db_connectivity", return_value=(False, "Connection refused")):
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["datasets_count"] == 0
        assert data["versions_count"] == 0
        assert data["total_runs_count"] == 0
        assert data["database_connected"] is False
        assert "Connection refused" in data["database_message"]
