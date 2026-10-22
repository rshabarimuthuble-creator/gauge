import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.models.dataset import EvaluationDataset
from app.models.agent_version import AgentVersion
from app.models.test_case import EvaluationTestCase
from app.models.evaluation_run import EvaluationRun


def create_seed_agent(db: Session, name="Reasoning Agent", version="v1.0.0") -> AgentVersion:
    agent = AgentVersion(
        name=name,
        version=version,
        model_provider="openai",
        model_name="gpt-4o",
        prompt_text="Solve the reasoning problem step by step.",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def create_seed_dataset(db: Session, name="Math Benchmark", cases=None) -> EvaluationDataset:
    dataset = EvaluationDataset(
        name=name,
        description="Math word problems with step-by-step reasoning",
    )
    db.add(dataset)
    db.flush()

    if cases:
        for idx, c in enumerate(cases, start=1):
            tc = EvaluationTestCase(
                dataset_id=dataset.id,
                case_identifier=c.get("case_identifier", f"tc-{idx}"),
                input_prompt=c["input_prompt"],
                expected_output=c.get("expected_output"),
                criteria=c.get("criteria"),
                metadata_json=json.dumps(c.get("metadata", {})) if c.get("metadata") else None,
            )
            db.add(tc)

    db.commit()
    db.refresh(dataset)
    return dataset


# 1. Successful evaluation with 100% pass rate
def test_successful_evaluation_all_passed(client: TestClient, db_session: Session):
    cases = [
        {"input_prompt": "What is 2 + 2?", "expected_output": "4"},
        {"input_prompt": "Capital of France?", "expected_output": "Paris"},
    ]
    dataset = create_seed_dataset(db_session, "Basic Q&A", cases=cases)
    agent = create_seed_agent(db_session, "General QA Agent")

    payload = {
        "name": "Q&A Run 1",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
    }
    response = client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["status"] == "completed"
    assert data["total_cases"] == 2
    assert data["passed_cases"] == 2
    assert data["failed_cases"] == 0
    assert data["errored_cases"] == 0
    assert data["unscored_cases"] == 0
    assert data["pass_rate"] == 100.0
    assert data["avg_latency_ms"] is not None
    assert len(data["results"]) == 2

    # Check case results details
    for res in data["results"]:
        assert res["status"] == "passed"
        assert res["actual_output"] == res["expected_output"]
        assert res["is_mock"] is True
        assert res["tokens_estimated"] is True
        assert res["latency_ms"] >= 0.0


# 2. Mixed correct and incorrect responses
def test_mixed_correct_and_incorrect_responses(client: TestClient, db_session: Session):
    cases = [
        {"input_prompt": "What is 5 * 5?", "expected_output": "25"},
        {"input_prompt": "What is 10 / 2?", "expected_output": "5"},
        {
            "input_prompt": "What is the speed of light? [SIMULATE_INCORRECT]",
            "expected_output": "299792458 m/s",
        },
        {
            "input_prompt": "Who wrote Hamlet? [SIMULATE_INCORRECT]",
            "expected_output": "William Shakespeare",
        },
    ]
    dataset = create_seed_dataset(db_session, "Mixed Benchmark", cases=cases)
    agent = create_seed_agent(db_session, "Test Agent")

    payload = {
        "name": "Mixed Evaluation Run",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
    }
    response = client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["status"] == "completed"
    assert data["total_cases"] == 4
    assert data["passed_cases"] == 2
    assert data["failed_cases"] == 2
    assert data["errored_cases"] == 0
    assert data["unscored_cases"] == 0
    # eligible_cases = 2 + 2 = 4; pass_rate = 2/4 * 100 = 50.0%
    assert data["pass_rate"] == 50.0


# 3. Execution exceptions and partial failures
def test_execution_exceptions_and_partial_failures(client: TestClient, db_session: Session):
    cases = [
        {"input_prompt": "Normal question 1", "expected_output": "Answer 1"},
        {
            "input_prompt": "Faulty prompt [SIMULATE_ERROR]",
            "expected_output": "Answer 2",
        },
        {"input_prompt": "Normal question 3", "expected_output": "Answer 3"},
    ]
    dataset = create_seed_dataset(db_session, "Fault Tolerance Benchmark", cases=cases)
    agent = create_seed_agent(db_session, "Robust Agent")

    response = client.post("/api/v1/evaluations", json={
        "name": "Fault Tolerance Run",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
    })
    assert response.status_code == 201
    data = response.json()

    assert data["status"] == "completed"
    assert data["total_cases"] == 3
    assert data["passed_cases"] == 2
    assert data["failed_cases"] == 0
    assert data["errored_cases"] == 1
    # Error case excluded from eligible denominator: eligible = 2 passed + 0 failed = 2
    # pass_rate = 2/2 * 100 = 100.0%
    assert data["pass_rate"] == 100.0

    # Verify error case details
    error_results = [r for r in data["results"] if r["status"] == "error"]
    assert len(error_results) == 1
    assert "error" in error_results[0]["status"]
    assert error_results[0]["error_message"] is not None
    assert "error" in error_results[0]["error_message"].lower()


# 4. Empty datasets
def test_empty_dataset_evaluation(client: TestClient, db_session: Session):
    dataset = create_seed_dataset(db_session, "Empty Benchmark", cases=[])
    agent = create_seed_agent(db_session, "Agent Empty")

    response = client.post("/api/v1/evaluations", json={
        "name": "Empty Run",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
    })
    assert response.status_code == 201
    data = response.json()

    assert data["status"] == "completed"
    assert data["total_cases"] == 0
    assert data["passed_cases"] == 0
    assert data["failed_cases"] == 0
    assert data["errored_cases"] == 0
    assert data["unscored_cases"] == 0
    assert data["pass_rate"] is None
    assert len(data["results"]) == 0


# 5. Missing expected outputs and unscored cases
def test_missing_expected_outputs_and_unscored_cases(client: TestClient, db_session: Session):
    cases = [
        {"input_prompt": "Scored question 1", "expected_output": "Answer 1"},
        {"input_prompt": "Open-ended prompt without answer", "expected_output": None},
        {"input_prompt": "Whitespace only answer prompt", "expected_output": "   "},
        {"input_prompt": "Scored question 2 [SIMULATE_INCORRECT]", "expected_output": "Answer 2"},
    ]
    dataset = create_seed_dataset(db_session, "Unscored Benchmark", cases=cases)
    agent = create_seed_agent(db_session, "Agent Mixed Scored")

    response = client.post("/api/v1/evaluations", json={
        "name": "Unscored Run",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
    })
    assert response.status_code == 201
    data = response.json()

    assert data["total_cases"] == 4
    assert data["passed_cases"] == 1
    assert data["failed_cases"] == 1
    assert data["unscored_cases"] == 2
    assert data["errored_cases"] == 0
    # eligible = 1 passed + 1 failed = 2. Pass rate = 1 / 2 * 100 = 50.0%
    assert data["pass_rate"] == 50.0

    unscored = [r for r in data["results"] if r["status"] == "unscored"]
    assert len(unscored) == 2


# 6. Invalid dataset and agent-version IDs return 404
def test_invalid_dataset_id_returns_404(client: TestClient, db_session: Session):
    agent = create_seed_agent(db_session)
    response = client.post("/api/v1/evaluations", json={
        "name": "Invalid Dataset Run",
        "dataset_id": "nonexistent-dataset-id",
        "agent_version_id": agent.id,
    })
    assert response.status_code == 404
    assert "dataset with ID" in response.json()["detail"]


def test_invalid_agent_version_id_returns_404(client: TestClient, db_session: Session):
    dataset = create_seed_dataset(db_session, "Test DS")
    response = client.post("/api/v1/evaluations", json={
        "name": "Invalid Agent Run",
        "dataset_id": dataset.id,
        "agent_version_id": "nonexistent-agent-id",
    })
    assert response.status_code == 404
    assert "Agent version with ID" in response.json()["detail"]


def test_get_nonexistent_run_returns_404(client: TestClient):
    response = client.get("/api/v1/evaluations/nonexistent-run-id")
    assert response.status_code == 404


def test_get_results_for_nonexistent_run_returns_404(client: TestClient):
    response = client.get("/api/v1/evaluations/nonexistent-run-id/results")
    assert response.status_code == 404


# 7. Aggregate metric calculations & latency statistics
def test_aggregate_metric_calculations_and_latency_stats(client: TestClient, db_session: Session):
    cases = [
        {"input_prompt": "Q1", "expected_output": "A1"},
        {"input_prompt": "Q2", "expected_output": "A2"},
        {"input_prompt": "Q3", "expected_output": "A3"},
    ]
    dataset = create_seed_dataset(db_session, "Latency Benchmark", cases=cases)
    agent = create_seed_agent(db_session)

    response = client.post("/api/v1/evaluations", json={
        "name": "Latency Run",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
    })
    assert response.status_code == 201
    data = response.json()

    assert data["min_latency_ms"] is not None
    assert data["max_latency_ms"] is not None
    assert data["avg_latency_ms"] is not None
    assert data["p95_latency_ms"] is not None
    assert data["min_latency_ms"] <= data["avg_latency_ms"] <= data["max_latency_ms"]


# 8. Persisted run and case-result retrieval
def test_persisted_run_and_case_result_retrieval(client: TestClient, db_session: Session):
    cases = [
        {"input_prompt": "Persist Test 1", "expected_output": "Answer 1"},
        {"input_prompt": "Persist Test 2 [SIMULATE_INCORRECT]", "expected_output": "Answer 2"},
    ]
    dataset = create_seed_dataset(db_session, "Persistence Test DS", cases=cases)
    agent = create_seed_agent(db_session)

    create_res = client.post("/api/v1/evaluations", json={
        "name": "Persistence Run",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
    })
    assert create_res.status_code == 201
    run_id = create_res.json()["id"]

    # 1. Fetch single run with details
    get_run_res = client.get(f"/api/v1/evaluations/{run_id}")
    assert get_run_res.status_code == 200
    run_detail = get_run_res.json()
    assert run_detail["id"] == run_id
    assert len(run_detail["results"]) == 2

    # 2. Fetch run case results via separate endpoint
    get_results_res = client.get(f"/api/v1/evaluations/{run_id}/results")
    assert get_results_res.status_code == 200
    all_results = get_results_res.json()
    assert len(all_results) == 2

    # 3. Filter results by status
    passed_only = client.get(f"/api/v1/evaluations/{run_id}/results?status=passed").json()
    assert len(passed_only) == 1
    assert passed_only[0]["status"] == "passed"

    failed_only = client.get(f"/api/v1/evaluations/{run_id}/results?status=failed").json()
    assert len(failed_only) == 1
    assert failed_only[0]["status"] == "failed"

    # 4. List evaluation runs
    list_runs_res = client.get("/api/v1/evaluations")
    assert list_runs_res.status_code == 200
    runs = list_runs_res.json()
    assert any(r["id"] == run_id for r in runs)


# 9. Database error handling
def test_evaluations_database_error_handling(client: TestClient):
    with patch("app.services.evaluation_service.EvaluationService.get_all", side_effect=OperationalError("Connection lost", {}, Exception())):
        response = client.get("/api/v1/evaluations")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "password" not in response.text.lower()


# 10. Repeated requests and idempotency
def test_repeated_evaluation_requests(client: TestClient, db_session: Session):
    """
    Proves that repeated evaluation requests against the same dataset and agent version:
    1. Create distinct EvaluationRun records with unique UUIDs.
    2. Invoke the adapter and create completely fresh EvaluationResult records (no row reuse).
    3. Ensure result foreign keys point exclusively to their own run_id.
    4. Preserve exact deterministic scoring (identical pass rates and counts).
    """
    cases = [
        {"input_prompt": "2 + 2", "expected_output": "4"},
        {"input_prompt": "Capital of Spain? [SIMULATE_INCORRECT]", "expected_output": "Madrid"},
        {"input_prompt": "Explain quantum physics", "expected_output": None},
    ]
    dataset = create_seed_dataset(db_session, "Idempotency DS", cases=cases)
    agent = create_seed_agent(db_session)

    # Launch two consecutive runs with identical parameters
    res1 = client.post("/api/v1/evaluations", json={
        "name": "Repeat Run 1",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
    })
    res2 = client.post("/api/v1/evaluations", json={
        "name": "Repeat Run 2",
        "dataset_id": dataset.id,
        "agent_version_id": agent.id,
    })

    assert res1.status_code == 201
    assert res2.status_code == 201

    data1 = res1.json()
    data2 = res2.json()

    # 1. Distinct runs with unique IDs
    id1 = data1["id"]
    id2 = data2["id"]
    assert id1 != id2

    # 2. Results are completely independent with disjoint UUIDs
    results1 = client.get(f"/api/v1/evaluations/{id1}/results").json()
    results2 = client.get(f"/api/v1/evaluations/{id2}/results").json()
    assert len(results1) == 3
    assert len(results2) == 3

    r1_ids = [r["id"] for r in results1]
    r2_ids = [r["id"] for r in results2]
    # No result ID is reused or shared between runs
    assert set(r1_ids).isdisjoint(set(r2_ids))

    # 3. Foreign keys correctly isolated to respective run_id
    assert all(r["run_id"] == id1 for r in results1)
    assert all(r["run_id"] == id2 for r in results2)

    # 4. Deterministic scoring preserved
    assert data1["total_cases"] == data2["total_cases"] == 3
    assert data1["passed_cases"] == data2["passed_cases"] == 1
    assert data1["failed_cases"] == data2["failed_cases"] == 1
    assert data1["unscored_cases"] == data2["unscored_cases"] == 1
    assert data1["pass_rate"] == data2["pass_rate"] == 50.0  # 1 passed / 2 eligible (1 passed + 1 failed) * 100
    assert data1["status"] == data2["status"] == "completed"


# 11. Dataset test-cases API
def test_dataset_test_cases_crud(client: TestClient):
    # Create dataset with initial test case
    create_payload = {
        "name": "GSM8K Extended",
        "description": "Benchmark with initial cases",
        "test_cases": [
            {
                "case_identifier": "gsm-1",
                "input_prompt": "Janet's ducks lay 16 eggs per day...",
                "expected_output": "16",
            }
        ],
    }
    create_res = client.post("/api/v1/datasets", json=create_payload)
    assert create_res.status_code == 201
    ds_id = create_res.json()["id"]
    assert create_res.json()["test_cases_count"] == 1

    # Add second test case via POST /datasets/{id}/cases
    case2_payload = {
        "case_identifier": "gsm-2",
        "input_prompt": "A bakery makes 20 loaves of bread...",
        "expected_output": "20",
    }
    case2_res = client.post(f"/api/v1/datasets/{ds_id}/cases", json=case2_payload)
    assert case2_res.status_code == 201
    assert case2_res.json()["case_identifier"] == "gsm-2"

    # Fetch test cases via GET /datasets/{id}/cases
    cases_res = client.get(f"/api/v1/datasets/{ds_id}/cases")
    assert cases_res.status_code == 200
    cases_list = cases_res.json()
    assert len(cases_list) == 2
    assert cases_list[0]["case_identifier"] == "gsm-1"
    assert cases_list[1]["case_identifier"] == "gsm-2"
