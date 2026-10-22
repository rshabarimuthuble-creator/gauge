from fastapi.testclient import TestClient


def test_get_datasets_empty(client: TestClient):
    """Test datasets endpoint returns empty list on initial setup."""
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get_dataset(client: TestClient):
    """Test creating a dataset and fetching it."""
    payload = {
        "name": "GSM8K Reasoning Benchmark",
        "description": "8,500 grade school math word problems",
    }
    create_res = client.post("/api/v1/datasets", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["name"] == payload["name"]
    assert created_data["description"] == payload["description"]
    assert "id" in created_data
    assert "created_at" in created_data
    assert "updated_at" in created_data

    # List datasets
    list_res = client.get("/api/v1/datasets")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["id"] == created_data["id"]

    # Get single dataset
    get_res = client.get(f"/api/v1/datasets/{created_data['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == payload["name"]


def test_create_dataset_validation_error(client: TestClient):
    """Test validation errors for invalid payload."""
    response = client.post("/api/v1/datasets", json={"name": ""})
    assert response.status_code == 422
