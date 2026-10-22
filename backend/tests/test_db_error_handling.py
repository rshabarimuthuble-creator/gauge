from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


def test_datasets_database_error_handling(client: TestClient):
    """Test that SQLAlchemy errors return 503 instead of crashing with uncaught 500 tracebacks."""
    with patch("app.services.dataset_service.DatasetService.get_all", side_effect=OperationalError("Connection lost", {}, Exception())):
        response = client.get("/api/v1/datasets")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "database" in data["detail"].lower() or "unavailable" in data["detail"].lower()
        # Verify no database credentials or internal driver details are leaked
        assert "password" not in response.text.lower()
        assert "psycopg2" not in response.text.lower()


def test_versions_database_error_handling(client: TestClient):
    """Test that SQLAlchemy errors on versions endpoint return 503 cleanly."""
    with patch("app.services.version_service.VersionService.get_all", side_effect=OperationalError("Connection lost", {}, Exception())):
        response = client.get("/api/v1/versions")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "password" not in response.text.lower()
