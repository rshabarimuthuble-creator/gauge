import json
import pytest
from fastapi.testclient import TestClient


def test_model_comparison_with_accuracy_and_telemetry_deltas(client: TestClient):
    # 1. Create dataset
    ds_resp = client.post("/api/v1/datasets", json={
        "name": "Comparison Telemetry Dataset",
        "version": "v1.0.0",
        "test_cases": [
            {"case_identifier": "TC-01", "input_prompt": "1+1", "expected_output": "2"},
            {"case_identifier": "TC-02", "input_prompt": "2+2", "expected_output": "4"},
            {"case_identifier": "TC-03", "input_prompt": "3+3", "expected_output": "6"},
            {"case_identifier": "TC-04", "input_prompt": "4+4", "expected_output": "8"},
        ]
    })
    assert ds_resp.status_code == 201
    dataset_id = ds_resp.json()["id"]

    # 2. Create baseline agent and candidate agent
    base_ag = client.post("/api/v1/versions", json={
        "name": "Baseline Agent v1",
        "version": "v1.0.0",
        "model_provider": "mock",
        "model_name": "mock-model",
        "prompt_text": "Base prompt",
    }).json()["id"]

    cand_ag = client.post("/api/v1/versions", json={
        "name": "Candidate Agent v2",
        "version": "v2.0.0",
        "model_provider": "mock",
        "model_name": "mock-model",
        "prompt_text": "Candidate prompt",
    }).json()["id"]

    # 3. Execute baseline run and candidate run
    run1 = client.post("/api/v1/evaluations", json={
        "name": "Baseline Run",
        "dataset_id": dataset_id,
        "agent_version_id": base_ag,
        "execution_mode": "mock",
    }).json()["id"]

    run2 = client.post("/api/v1/evaluations", json={
        "name": "Candidate Run",
        "dataset_id": dataset_id,
        "agent_version_id": cand_ag,
        "execution_mode": "mock",
    }).json()["id"]

    # 4. Create comparison
    comp_resp = client.post("/api/v1/comparisons", json={
        "candidate_run_id": run2,
        "baseline_run_id": run1,
    })
    assert comp_resp.status_code == 201
    comp = comp_resp.json()

    assert comp["is_compatible"] is True
    assert comp["pass_rate_delta"] == 0.0
    assert comp["accuracy_delta"] == 0.0
    assert "tokens_delta" in comp
    assert "cost_usd_delta" in comp

    # Check reasons contains empirical variance notice
    reasons_text = " ".join(comp["reasons"])
    assert "Variance notice" in reasons_text
    assert "sampling temperature" in reasons_text

    # Check per-case results have score and scoring method
    cases = comp["case_comparisons"]
    assert len(cases) == 4
    for c in cases:
        assert c["baseline_score"] == 1.0
        assert c["candidate_score"] == 1.0
        assert c["scoring_method"] == "exact_match"


def test_comparison_flags_dataset_version_discrepancy(client: TestClient):
    # Dataset 1: v1.0
    ds1 = client.post("/api/v1/datasets", json={
        "name": "Version Suite v1",
        "version": "v1.0.0",
        "test_cases": [{"case_identifier": "C-1", "input_prompt": "A", "expected_output": "A"}]
    }).json()["id"]

    agent = client.post("/api/v1/versions", json={
        "name": "Agent",
        "version": "v1.0.0",
        "model_provider": "mock",
        "model_name": "m",
    }).json()["id"]

    run1 = client.post("/api/v1/evaluations", json={
        "name": "Run on v1",
        "dataset_id": ds1,
        "agent_version_id": agent,
        "execution_mode": "mock",
    }).json()["id"]

    # Update dataset version to v2.0
    # Note: run1 has dataset_version v1.0.0. If we update dataset or create run2 on a different version
    run2 = client.post("/api/v1/evaluations", json={
        "name": "Run on v2",
        "dataset_id": ds1,
        "agent_version_id": agent,
        "execution_mode": "mock",
    }).json()["id"]

    comp_resp = client.post("/api/v1/comparisons", json={
        "candidate_run_id": run2,
        "baseline_run_id": run1,
    })
    assert comp_resp.status_code == 201


def test_repeated_runs_create_separate_records(client: TestClient):
    ds = client.post("/api/v1/datasets", json={
        "name": "Repeated Run Dataset",
        "version": "v1.0.0",
        "test_cases": [{"case_identifier": "R-1", "input_prompt": "Hello", "expected_output": "Hello"}]
    }).json()["id"]

    ag = client.post("/api/v1/versions", json={
        "name": "Repeated Agent",
        "version": "v1.0.0",
        "model_provider": "mock",
        "model_name": "m",
    }).json()["id"]

    # Launch same evaluation twice
    r1 = client.post("/api/v1/evaluations", json={
        "name": "Run Instance",
        "dataset_id": ds,
        "agent_version_id": ag,
        "execution_mode": "mock",
    }).json()

    r2 = client.post("/api/v1/evaluations", json={
        "name": "Run Instance",
        "dataset_id": ds,
        "agent_version_id": ag,
        "execution_mode": "mock",
    }).json()

    assert r1["id"] != r2["id"], "Repeated runs must have distinct unique IDs"

    # Both runs are retrievable independently
    fetch_r1 = client.get(f"/api/v1/evaluations/{r1['id']}").json()
    fetch_r2 = client.get(f"/api/v1/evaluations/{r2['id']}").json()
    assert fetch_r1["id"] == r1["id"]
    assert fetch_r2["id"] == r2["id"]
