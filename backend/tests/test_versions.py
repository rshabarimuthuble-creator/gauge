from fastapi.testclient import TestClient


def test_get_versions_empty(client: TestClient):
    """Test versions endpoint returns empty list initially."""
    response = client.get("/api/v1/versions")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get_version(client: TestClient):
    """Test registering an agent version and retrieving it."""
    payload = {
        "name": "SQL Agent",
        "version": "1.2.0",
        "model_provider": "anthropic",
        "model_name": "claude-3-5-sonnet-20241022",
        "prompt_text": "You are an expert SQL generator.",
    }
    create_res = client.post("/api/v1/versions", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["name"] == payload["name"]
    assert created_data["version"] == payload["version"]
    assert created_data["model_provider"] == payload["model_provider"]
    assert "id" in created_data

    # List versions
    list_res = client.get("/api/v1/versions")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["id"] == created_data["id"]

    # Get single version
    get_res = client.get(f"/api/v1/versions/{created_data['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == payload["name"]


def test_get_nonexistent_version_returns_404(client: TestClient):
    """Test retrieving nonexistent version returns 404."""
    response = client.get("/api/v1/versions/non-existent-id")
    assert response.status_code == 404
