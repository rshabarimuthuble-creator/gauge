import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.dataset import EvaluationDataset
from app.models.test_case import EvaluationTestCase
from app.services.dataset_service import DatasetService, DatasetDuplicateError, DatasetValidationError


def test_curated_benchmark_fixture_integrity():
    fixture_path = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "curated_benchmark_dataset.json"
    assert fixture_path.exists(), "Curated benchmark dataset fixture must exist"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["name"] == "Gauge General Reasoning & Capabilities Suite"
    assert "v1." in data["version"]
    assert "synthetic" in data["provenance"].lower(), "Provenance must be honestly declared as synthetic"

    test_cases = data["test_cases"]
    assert len(test_cases) >= 30, f"Expected 30-50 test cases, found {len(test_cases)}"

    # Validate stable unique IDs
    case_ids = [tc["case_identifier"] for tc in test_cases]
    assert len(case_ids) == len(set(case_ids)), "Test case IDs must be unique"

    # Validate categories and difficulties
    categories = {tc.get("category") for tc in test_cases}
    assert "mathematics" in categories
    assert "logic" in categories
    assert "knowledge" in categories
    assert "structured_json" in categories
    assert "multi_part" in categories
    assert "edge_case" in categories

    for tc in test_cases:
        assert tc.get("input_prompt"), f"Case {tc['case_identifier']} missing input_prompt"
        assert tc.get("scoring_method"), f"Case {tc['case_identifier']} missing scoring_method"


def test_dataset_json_import(client: TestClient):
    payload = {
        "content": json.dumps({
            "name": "Imported Test Suite",
            "version": "v1.2.0",
            "description": "JSON Import validation",
            "test_cases": [
                {
                    "case_identifier": "IMP-01",
                    "input_prompt": "What is 1 + 1?",
                    "expected_output": "2",
                    "category": "math",
                    "difficulty": "easy",
                    "scoring_method": "exact_match",
                },
                {
                    "case_identifier": "IMP-02",
                    "input_prompt": "What is 2 + 2?",
                    "expected_output": "4",
                    "category": "math",
                    "difficulty": "easy",
                    "scoring_method": "exact_match",
                }
            ]
        })
    }
    response = client.post("/api/v1/datasets/import", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Imported Test Suite"
    assert data["version"] == "v1.2.0"
    assert data["test_cases_count"] == 2


def test_dataset_jsonl_import(client: TestClient):
    jsonl_content = (
        '{"case_identifier": "JSONL-01", "input_prompt": "Prompt 1", "expected_output": "Ans 1"}\n'
        '{"case_identifier": "JSONL-02", "input_prompt": "Prompt 2", "expected_output": "Ans 2"}\n'
        '{"case_identifier": "JSONL-03", "input_prompt": "Prompt 3", "expected_output": "Ans 3"}'
    )
    payload = {
        "name": "JSONL Benchmark Suite",
        "content": jsonl_content,
    }
    response = client.post("/api/v1/datasets/import", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "JSONL Benchmark Suite"
    assert data["test_cases_count"] == 3


def test_dataset_import_rejects_duplicate_ids(client: TestClient):
    # Duplicate case_identifier within payload
    duplicate_payload = {
        "content": json.dumps({
            "name": "Duplicate ID Suite",
            "test_cases": [
                {"case_identifier": "DUP-01", "input_prompt": "Prompt A", "expected_output": "A"},
                {"case_identifier": "DUP-01", "input_prompt": "Prompt B", "expected_output": "B"},
            ]
        })
    }
    response = client.post("/api/v1/datasets/import", json=duplicate_payload)
    assert response.status_code == 400
    assert "Duplicate case_identifier 'DUP-01'" in response.json()["detail"]


def test_dataset_import_rejects_malformed_json(client: TestClient):
    malformed_payload = {
        "content": '{"name": "Bad Suite", test_cases: [bad_json]}'
    }
    response = client.post("/api/v1/datasets/import", json=malformed_payload)
    assert response.status_code == 400
    assert "Malformed" in response.json()["detail"]


def test_dataset_snapshot_behavior_on_evaluation_run(client: TestClient):
    # 1. Create a versioned dataset
    ds_resp = client.post("/api/v1/datasets", json={
        "name": "Snapshot Test Benchmark",
        "version": "v2.5.0",
        "description": "Verifying immutable snapshotting",
        "test_cases": [
            {"case_identifier": "SNAP-01", "input_prompt": "2 + 2", "expected_output": "4"},
            {"case_identifier": "SNAP-02", "input_prompt": "3 + 3", "expected_output": "6"},
        ]
    })
    assert ds_resp.status_code == 201
    dataset = ds_resp.json()
    dataset_id = dataset["id"]

    # 2. Create agent version
    ag_resp = client.post("/api/v1/versions", json={
        "name": "Snapshot Test Agent",
        "version": "v1.0.0",
        "model_provider": "mock",
        "model_name": "mock-eval",
        "prompt_text": "Answer accurately",
    })
    assert ag_resp.status_code == 201
    agent_id = ag_resp.json()["id"]

    # 3. Launch evaluation run
    run_resp = client.post("/api/v1/evaluations", json={
        "name": "Snapshot Verification Run",
        "dataset_id": dataset_id,
        "agent_version_id": agent_id,
        "execution_mode": "mock",
    })
    assert run_resp.status_code == 201
    run_data = run_resp.json()

    # Verify run captured dataset version and immutable snapshot
    assert run_data["dataset_version"] == "v2.5.0"
    assert run_data["dataset_snapshot_json"] is not None
    snapshot = json.loads(run_data["dataset_snapshot_json"])
    assert len(snapshot) == 2
    assert snapshot[0]["case_identifier"] == "SNAP-01"
    assert snapshot[1]["case_identifier"] == "SNAP-02"

    # 4. Modify dataset by adding another test case
    add_resp = client.post(f"/api/v1/datasets/{dataset_id}/cases", json={
        "case_identifier": "SNAP-03",
        "input_prompt": "4 + 4",
        "expected_output": "8",
    })
    assert add_resp.status_code == 201

    # 5. Fetch prior run details again and verify snapshot remains unchanged
    refetched_run = client.get(f"/api/v1/evaluations/{run_data['id']}").json()
    refetched_snapshot = json.loads(refetched_run["dataset_snapshot_json"])
    assert len(refetched_snapshot) == 2, "Run snapshot must remain immutable even when dataset changes"
    assert refetched_run["total_cases"] == 2
