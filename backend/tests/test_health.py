from unittest.mock import patch
from fastapi.testclient import TestClient


def test_health_endpoint_healthy(client: TestClient):
    """Test that /health returns 200 with appropriate structure when DB is accessible."""
    with patch("app.main.check_db_connectivity", return_value=(True, "Database connected")):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "gauge-backend"
        assert "version" in data
        assert "environment" in data
        assert data["database"]["connected"] is True
        assert data["database"]["message"] == "Database connected"
        assert "timestamp" in data


def test_health_endpoint_degraded_when_db_down(client: TestClient):
    """Test that /health correctly reports 'degraded' when database is unreachable."""
    with patch("app.main.check_db_connectivity", return_value=(False, "Database connection rejected")):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"]["connected"] is False
        assert "Database connection rejected" in data["database"]["message"]


def test_root_endpoint(client: TestClient):
    """Test root endpoint returns discovery metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Gauge"
    assert "docs_url" in data
    assert "health_url" in data
