import json
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.dataset import EvaluationDataset
from app.models.agent_version import AgentVersion
from app.models.test_case import EvaluationTestCase
from app.models.evaluation_run import EvaluationRun
from app.models.evaluation_result import EvaluationResult
from app.models.baseline import EvaluationBaseline
from app.models.comparison import EvaluationComparison


def create_agent(db: Session, name="Reasoning Agent", version="v1.0.0") -> AgentVersion:
    agent = AgentVersion(
        name=name,
        version=version,
        model_provider="openai",
        model_name="gpt-4o",
        prompt_text="Solve step by step.",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def create_dataset(db: Session, name="Benchmark Dataset", cases=None) -> EvaluationDataset:
    dataset = EvaluationDataset(
        name=name,
        description="Dataset for testing comparisons and regressions",
    )
    db.add(dataset)
    db.flush()

    if cases:
        for idx, c in enumerate(cases, start=1):
            tc = EvaluationTestCase(
                dataset_id=dataset.id,
                case_identifier=c.get("case_identifier", f"case-{idx}"),
                input_prompt=c["input_prompt"],
                expected_output=c.get("expected_output"),
            )
            db.add(tc)

    db.commit()
    db.refresh(dataset)
    return dataset


def create_mock_run(
    db: Session,
    dataset: EvaluationDataset,
    agent: AgentVersion,
    name: str = "Test Run",
    status: str = "completed",
    case_results: list = None,
    avg_latency_ms: float = 120.0,
    p95_latency_ms: float = 150.0,
) -> EvaluationRun:
    """Helper to construct evaluation runs with explicit case results for comparison testing."""
    run = EvaluationRun(
        name=name,
        status=status,
        dataset_id=dataset.id,
        agent_version_id=agent.id,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc) if status == "completed" else None,
        avg_latency_ms=avg_latency_ms if status == "completed" else None,
        p95_latency_ms=p95_latency_ms if status == "completed" else None,
    )
    db.add(run)
    db.flush()

    if case_results:
        total = len(case_results)
        passed = sum(1 for c in case_results if c.get("status") == "passed")
        failed = sum(1 for c in case_results if c.get("status") == "failed")
        errored = sum(1 for c in case_results if c.get("status") == "error")
        unscored = sum(1 for c in case_results if c.get("status") == "unscored")

        run.total_cases = total
        run.passed_cases = passed
        run.failed_cases = failed
        run.errored_cases = errored
        run.unscored_cases = unscored
        scored = passed + failed
        run.pass_rate = round((passed / scored) * 100.0, 2) if scored > 0 else 0.0

        for c in case_results:
            res = EvaluationResult(
                run_id=run.id,
                case_identifier=c["case_identifier"],
                input_prompt=c.get("input_prompt", "prompt"),
                expected_output=c.get("expected_output", "expected"),
                actual_output=c.get("actual_output", "actual"),
                status=c.get("status", "passed"),
                latency_ms=c.get("latency_ms", 100.0),
                token_usage=25,
                tokens_estimated=True,
                is_mock=True,
            )
            db.add(res)

    db.commit()
    db.refresh(run)
    return run


# ==========================================
# 1. BASELINE MANAGEMENT TESTS
# ==========================================

def test_set_valid_baseline(client: TestClient, db_session: Session):
    agent = create_agent(db_session, "Agent-1", "v1.0")
    dataset = create_dataset(db_session, "Benchmark-A")
    run = create_mock_run(
        db_session,
        dataset,
        agent,
        name="Baseline Run 1",
        status="completed",
        case_results=[
            {"case_identifier": "c1", "status": "passed"},
            {"case_identifier": "c2", "status": "failed"},
        ],
    )

    response = client.put(
        "/api/v1/baselines",
        json={"dataset_id": dataset.id, "run_id": run.id, "notes": "Production golden baseline"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == dataset.id
    assert data["run_id"] == run.id
    assert data["is_active"] is True
    assert data["notes"] == "Production golden baseline"
    assert data["agent_name"] == "Agent-1"
    assert data["pass_rate"] == 50.0


def test_replace_baseline_preserves_history(client: TestClient, db_session: Session):
    agent = create_agent(db_session, "Agent-1", "v1.0")
    dataset = create_dataset(db_session, "Benchmark-A")
    run1 = create_mock_run(
        db_session,
        dataset,
        agent,
        name="Run 1",
        case_results=[{"case_identifier": "c1", "status": "passed"}],
    )
    run2 = create_mock_run(
        db_session,
        dataset,
        agent,
        name="Run 2",
        case_results=[{"case_identifier": "c1", "status": "passed"}],
    )

    # Set run1 as baseline
    res1 = client.put("/api/v1/baselines", json={"dataset_id": dataset.id, "run_id": run1.id})
    assert res1.status_code == 200

    # Set run2 as new baseline
    res2 = client.put("/api/v1/baselines", json={"dataset_id": dataset.id, "run_id": run2.id, "notes": "Updated baseline"})
    assert res2.status_code == 200
    assert res2.json()["run_id"] == run2.id

    # Active baseline must be run2
    active_res = client.get(f"/api/v1/baselines/{dataset.id}")
    assert active_res.status_code == 200
    assert active_res.json()["run_id"] == run2.id
    assert active_res.json()["is_active"] is True

    # History should contain both baselines
    history_res = client.get(f"/api/v1/baselines/{dataset.id}/history")
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 2
    assert history[0]["run_id"] == run2.id and history[0]["is_active"] is True
    assert history[1]["run_id"] == run1.id and history[1]["is_active"] is False


def test_reject_incomplete_or_empty_run_as_baseline(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)

    # Pending run
    pending_run = create_mock_run(
        db_session, dataset, agent, status="pending",
        case_results=[{"case_identifier": "c1", "status": "passed"}],
    )
    res_pending = client.put("/api/v1/baselines", json={"dataset_id": dataset.id, "run_id": pending_run.id})
    assert res_pending.status_code == 400
    assert "status is 'pending', expected 'completed'" in res_pending.json()["detail"]

    # Empty run (0 cases)
    empty_run = create_mock_run(db_session, dataset, agent, status="completed", case_results=[])
    res_empty = client.put("/api/v1/baselines", json={"dataset_id": dataset.id, "run_id": empty_run.id})
    assert res_empty.status_code == 400
    assert "0 test cases" in res_empty.json()["detail"]


def test_reject_mismatched_dataset_for_baseline(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset_a = create_dataset(db_session, "Dataset A")
    dataset_b = create_dataset(db_session, "Dataset B")
    run_a = create_mock_run(
        db_session, dataset_a, agent,
        case_results=[{"case_identifier": "c1", "status": "passed"}],
    )

    # Attempt to assign run_a to dataset_b
    res = client.put("/api/v1/baselines", json={"dataset_id": dataset_b.id, "run_id": run_a.id})
    assert res.status_code == 400
    assert "belongs to dataset" in res.json()["detail"]


# ==========================================
# 2. COMPARISON & REGRESSION DETECTION TESTS
# ==========================================

def test_compare_identical_runs_unchanged(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)
    case_results = [
        {"case_identifier": "c1", "status": "passed", "latency_ms": 100.0},
        {"case_identifier": "c2", "status": "failed", "latency_ms": 120.0},
    ]
    base_run = create_mock_run(db_session, dataset, agent, name="Base", case_results=case_results, avg_latency_ms=110.0, p95_latency_ms=120.0)
    cand_run = create_mock_run(db_session, dataset, agent, name="Cand", case_results=case_results, avg_latency_ms=110.0, p95_latency_ms=120.0)

    # Designate baseline
    client.put("/api/v1/baselines", json={"dataset_id": dataset.id, "run_id": base_run.id})

    # Compare without specifying baseline_run_id (uses active baseline)
    res = client.post("/api/v1/comparisons", json={"candidate_run_id": cand_run.id})
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "unchanged"
    assert data["pass_rate_delta"] == 0.0
    assert data["avg_latency_ms_delta"] == 0.0
    assert data["newly_failing_count"] == 0
    assert data["newly_fixed_count"] == 0
    assert any("Mock execution detected" in r for r in data["reasons"])


def test_compare_improved_pass_rate(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)
    base_cases = [
        {"case_identifier": "c1", "status": "passed"},
        {"case_identifier": "c2", "status": "failed"},
    ]
    cand_cases = [
        {"case_identifier": "c1", "status": "passed"},
        {"case_identifier": "c2", "status": "passed"},  # fixed!
    ]
    base_run = create_mock_run(db_session, dataset, agent, name="Base", case_results=base_cases)
    cand_run = create_mock_run(db_session, dataset, agent, name="Cand", case_results=cand_cases)

    res = client.post(
        "/api/v1/comparisons",
        json={"candidate_run_id": cand_run.id, "baseline_run_id": base_run.id},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "improved"
    # 50.0% to 100.0% is +50.0 percentage points
    assert data["pass_rate_delta"] == 50.0
    assert data["newly_fixed_count"] == 1
    assert data["newly_failing_count"] == 0


def test_compare_regressed_pass_rate(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)
    base_cases = [
        {"case_identifier": "c1", "status": "passed"},
        {"case_identifier": "c2", "status": "passed"},
    ]
    cand_cases = [
        {"case_identifier": "c1", "status": "passed"},
        {"case_identifier": "c2", "status": "failed"},  # newly failing!
    ]
    base_run = create_mock_run(db_session, dataset, agent, name="Base", case_results=base_cases)
    cand_run = create_mock_run(db_session, dataset, agent, name="Cand", case_results=cand_cases)

    res = client.post(
        "/api/v1/comparisons",
        json={"candidate_run_id": cand_run.id, "baseline_run_id": base_run.id},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "regressed"
    # 100.0% to 50.0% is -50.0 percentage points
    assert data["pass_rate_delta"] == -50.0
    assert data["newly_failing_count"] == 1
    assert any("Pass rate declined by 50.0 percentage points" in r for r in data["reasons"])


def test_compare_latency_regression(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)
    cases = [{"case_identifier": "c1", "status": "passed"}]
    base_run = create_mock_run(db_session, dataset, agent, name="Base", case_results=cases, avg_latency_ms=100.0, p95_latency_ms=120.0)
    cand_run = create_mock_run(db_session, dataset, agent, name="Cand", case_results=cases, avg_latency_ms=250.0, p95_latency_ms=300.0)

    # Average latency increase +150ms > default 100ms threshold
    res = client.post(
        "/api/v1/comparisons",
        json={"candidate_run_id": cand_run.id, "baseline_run_id": base_run.id},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "regressed"
    assert data["avg_latency_ms_delta"] == 150.0
    assert any("Average latency increased by 150.0 ms" in r for r in data["reasons"])


def test_compare_error_count_regression(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)
    base_cases = [{"case_identifier": "c1", "status": "passed"}]
    cand_cases = [{"case_identifier": "c1", "status": "error"}]
    base_run = create_mock_run(db_session, dataset, agent, name="Base", case_results=base_cases)
    cand_run = create_mock_run(db_session, dataset, agent, name="Cand", case_results=cand_cases)

    res = client.post(
        "/api/v1/comparisons",
        json={"candidate_run_id": cand_run.id, "baseline_run_id": base_run.id},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "regressed"
    assert data["errored_cases_delta"] == 1
    assert data["newly_errored_count"] == 1
    assert any("Execution error count increased by 1" in r for r in data["reasons"])


def test_compare_mixed_outcomes(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)
    # Pass rate improves (+33 pp), but latency regresses (+150ms)
    base_cases = [
        {"case_identifier": "c1", "status": "passed"},
        {"case_identifier": "c2", "status": "failed"},
        {"case_identifier": "c3", "status": "failed"},
    ]
    cand_cases = [
        {"case_identifier": "c1", "status": "passed"},
        {"case_identifier": "c2", "status": "passed"},  # fixed
        {"case_identifier": "c3", "status": "failed"},
    ]
    base_run = create_mock_run(db_session, dataset, agent, name="Base", case_results=base_cases, avg_latency_ms=100.0)
    cand_run = create_mock_run(db_session, dataset, agent, name="Cand", case_results=cand_cases, avg_latency_ms=250.0)

    res = client.post(
        "/api/v1/comparisons",
        json={"candidate_run_id": cand_run.id, "baseline_run_id": base_run.id},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "mixed"
    assert any("Pass rate improved" in r for r in data["reasons"])
    assert any("Average latency increased" in r for r in data["reasons"])


def test_compare_incompatible_datasets(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset_a = create_dataset(db_session, "Dataset Alpha")
    dataset_b = create_dataset(db_session, "Dataset Beta")
    run_a = create_mock_run(db_session, dataset_a, agent, case_results=[{"case_identifier": "c1", "status": "passed"}])
    run_b = create_mock_run(db_session, dataset_b, agent, case_results=[{"case_identifier": "c1", "status": "passed"}])

    res = client.post(
        "/api/v1/comparisons",
        json={"candidate_run_id": run_b.id, "baseline_run_id": run_a.id},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["is_compatible"] is False
    assert data["status"] == "inconclusive"
    assert "Dataset mismatch" in data["compatibility_notes"]


def test_compare_version_to_version(client: TestClient, db_session: Session):
    agent_v1 = create_agent(db_session, name="CodeAgent", version="v1.0.0")
    agent_v2 = create_agent(db_session, name="CodeAgent", version="v2.0.0")
    dataset = create_dataset(db_session, "Coding Eval")

    base_cases = [{"case_identifier": "c1", "status": "failed"}]
    cand_cases = [{"case_identifier": "c1", "status": "passed"}]

    run_v1 = create_mock_run(db_session, dataset, agent_v1, name="v1 Run", case_results=base_cases)
    run_v2 = create_mock_run(db_session, dataset, agent_v2, name="v2 Run", case_results=cand_cases)

    res = client.post(
        "/api/v1/comparisons",
        json={"candidate_run_id": run_v2.id, "baseline_run_id": run_v1.id},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["baseline_agent_version"] == "v1.0.0"
    assert data["candidate_agent_version"] == "v2.0.0"
    assert data["status"] == "improved"


def test_get_comparison_detail_and_regressions_endpoint(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)
    base_cases = [
        {"case_identifier": "c1", "status": "passed"},
        {"case_identifier": "c2", "status": "passed"},
    ]
    cand_cases = [
        {"case_identifier": "c1", "status": "passed"},
        {"case_identifier": "c2", "status": "failed"},  # newly failing
    ]
    base_run = create_mock_run(db_session, dataset, agent, case_results=base_cases)
    cand_run = create_mock_run(db_session, dataset, agent, case_results=cand_cases)

    create_res = client.post(
        "/api/v1/comparisons",
        json={"candidate_run_id": cand_run.id, "baseline_run_id": base_run.id},
    )
    assert create_res.status_code == 201
    comp_id = create_res.json()["id"]

    # Test GET /comparisons/{id}
    detail_res = client.get(f"/api/v1/comparisons/{comp_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == comp_id
    assert len(detail["case_comparisons"]) == 2
    c2_diff = next(c for c in detail["case_comparisons"] if c["case_identifier"] == "c2")
    assert c2_diff["outcome_change"] == "newly_failing"
    assert c2_diff["baseline_status"] == "passed"
    assert c2_diff["candidate_status"] == "failed"

    # Test GET /comparisons/{id}/regressions
    reg_res = client.get(f"/api/v1/comparisons/{comp_id}/regressions")
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert reg_data["status"] == "regressed"
    assert reg_data["newly_failing_count"] == 1
    assert len(reg_data["newly_failing_cases"]) == 1
    assert reg_data["newly_failing_cases"][0]["case_identifier"] == "c2"


def test_custom_thresholds_override(client: TestClient, db_session: Session):
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)
    cases = [{"case_identifier": "c1", "status": "passed"}]
    # Latency increased by 60ms. Default threshold is 100ms (so default would be 'unchanged')
    # But if we configure custom threshold of 50ms, it should detect latency regression!
    base_run = create_mock_run(db_session, dataset, agent, case_results=cases, avg_latency_ms=100.0)
    cand_run = create_mock_run(db_session, dataset, agent, case_results=cases, avg_latency_ms=160.0)

    res = client.post(
        "/api/v1/comparisons",
        json={
            "candidate_run_id": cand_run.id,
            "baseline_run_id": base_run.id,
            "thresholds": {
                "latency_increase_threshold_ms": 50.0,
            },
        },
    )
    assert res.status_code == 201
    assert res.json()["status"] == "regressed"
    assert any("Average latency increased by 60.0 ms (threshold: 50.0 ms)" in r for r in res.json()["reasons"])


# ==========================================
# 3. FOCUSED FINAL VERIFICATION TESTS
# ==========================================

def test_sub_millisecond_latency_delta_and_negative_zero_handling(client: TestClient, db_session: Session):
    """
    Verifies that a baseline of 5.23 ms and candidate of 5.19 ms produces exactly -0.04 ms delta,
    and identical latencies do not serialize as negative zero (-0.0).
    """
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)
    cases = [{"case_identifier": "c1", "status": "passed"}]

    base_run = create_mock_run(db_session, dataset, agent, case_results=cases, avg_latency_ms=5.23, p95_latency_ms=6.00)
    cand_run = create_mock_run(db_session, dataset, agent, case_results=cases, avg_latency_ms=5.19, p95_latency_ms=6.00)

    res = client.post(
        "/api/v1/comparisons",
        json={"candidate_run_id": cand_run.id, "baseline_run_id": base_run.id},
    )
    assert res.status_code == 201
    data = res.json()
    # 5.19 - 5.23 = -0.04 ms (candidate is 0.04 ms faster)
    assert data["avg_latency_ms_delta"] == -0.04
    # P95 latencies are identical (6.00 - 6.00 = 0.0, strictly not -0.0)
    assert data["p95_latency_ms_delta"] == 0.0
    assert str(data["p95_latency_ms_delta"]) == "0.0"


def test_regression_threshold_boundary_pass_rate_decline():
    """
    Verifies pass-rate decline threshold boundary behavior:
    Immediately below (4.9 pp), exactly at (5.0 pp), and above (5.1 pp) for a 5.0 pp threshold.
    """
    from app.services.comparison_service import ComparisonService
    from app.schemas.comparison import RegressionThresholds

    thresholds = RegressionThresholds(pass_rate_decline_threshold=5.0)

    # 1. Immediately below: 4.9 pp decline (pass_rate_delta = -4.9)
    status_below, reasons_below = ComparisonService.classify_regression(
        is_compatible=True,
        compatibility_notes="Full benchmark coverage match",
        pass_rate_delta=-4.9,
        avg_latency_ms_delta=0.0,
        p95_latency_ms_delta=0.0,
        errored_cases_delta=0,
        newly_failing_count=0,
        newly_fixed_count=0,
        thresholds=thresholds,
        is_all_mock=False,
    )
    assert status_below == "unchanged"
    assert not any("Pass rate declined" in r for r in reasons_below)

    # 2. Exactly at threshold: 5.0 pp decline (pass_rate_delta = -5.0)
    status_at, reasons_at = ComparisonService.classify_regression(
        is_compatible=True,
        compatibility_notes="Full benchmark coverage match",
        pass_rate_delta=-5.0,
        avg_latency_ms_delta=0.0,
        p95_latency_ms_delta=0.0,
        errored_cases_delta=0,
        newly_failing_count=0,
        newly_fixed_count=0,
        thresholds=thresholds,
        is_all_mock=False,
    )
    assert status_at == "unchanged"
    assert not any("Pass rate declined" in r for r in reasons_at)

    # 3. Immediately above: 5.1 pp decline (pass_rate_delta = -5.1)
    status_above, reasons_above = ComparisonService.classify_regression(
        is_compatible=True,
        compatibility_notes="Full benchmark coverage match",
        pass_rate_delta=-5.1,
        avg_latency_ms_delta=0.0,
        p95_latency_ms_delta=0.0,
        errored_cases_delta=0,
        newly_failing_count=0,
        newly_fixed_count=0,
        thresholds=thresholds,
        is_all_mock=False,
    )
    assert status_above == "regressed"
    assert any("Pass rate declined by 5.1 percentage points (threshold: 5.0 pp)" in r for r in reasons_above)


def test_regression_threshold_boundary_latency_increase():
    """
    Verifies average latency increase threshold boundary behavior:
    Immediately below (99.9 ms), exactly at (100.0 ms), and above (100.1 ms) for a 100.0 ms threshold.
    """
    from app.services.comparison_service import ComparisonService
    from app.schemas.comparison import RegressionThresholds

    thresholds = RegressionThresholds(latency_increase_threshold_ms=100.0)

    # 1. Immediately below (+99.9 ms)
    status_below, reasons_below = ComparisonService.classify_regression(
        is_compatible=True,
        compatibility_notes="Full benchmark coverage match",
        pass_rate_delta=0.0,
        avg_latency_ms_delta=99.9,
        p95_latency_ms_delta=0.0,
        errored_cases_delta=0,
        newly_failing_count=0,
        newly_fixed_count=0,
        thresholds=thresholds,
        is_all_mock=False,
    )
    assert status_below == "unchanged"
    assert not any("Average latency increased" in r for r in reasons_below)

    # 2. Exactly at threshold (+100.0 ms)
    status_at, reasons_at = ComparisonService.classify_regression(
        is_compatible=True,
        compatibility_notes="Full benchmark coverage match",
        pass_rate_delta=0.0,
        avg_latency_ms_delta=100.0,
        p95_latency_ms_delta=0.0,
        errored_cases_delta=0,
        newly_failing_count=0,
        newly_fixed_count=0,
        thresholds=thresholds,
        is_all_mock=False,
    )
    assert status_at == "unchanged"
    assert not any("Average latency increased" in r for r in reasons_at)

    # 3. Immediately above (+100.1 ms)
    status_above, reasons_above = ComparisonService.classify_regression(
        is_compatible=True,
        compatibility_notes="Full benchmark coverage match",
        pass_rate_delta=0.0,
        avg_latency_ms_delta=100.1,
        p95_latency_ms_delta=0.0,
        errored_cases_delta=0,
        newly_failing_count=0,
        newly_fixed_count=0,
        thresholds=thresholds,
        is_all_mock=False,
    )
    assert status_above == "regressed"
    assert any("Average latency increased by 100.1 ms (threshold: 100.0 ms)" in r for r in reasons_above)


def test_regression_threshold_boundary_error_count():
    """
    Verifies error count increase threshold boundary behavior:
    With threshold=2: 1 error (below), 2 errors (at), 3 errors (above).
    """
    from app.services.comparison_service import ComparisonService
    from app.schemas.comparison import RegressionThresholds

    thresholds = RegressionThresholds(error_count_increase_threshold=2)

    # 1. Below threshold (1 new error)
    status_below, reasons_below = ComparisonService.classify_regression(
        is_compatible=True,
        compatibility_notes="Full benchmark coverage match",
        pass_rate_delta=0.0,
        avg_latency_ms_delta=0.0,
        p95_latency_ms_delta=0.0,
        errored_cases_delta=1,
        newly_failing_count=0,
        newly_fixed_count=0,
        thresholds=thresholds,
        is_all_mock=False,
    )
    assert status_below == "unchanged"

    # 2. At threshold (2 new errors)
    status_at, reasons_at = ComparisonService.classify_regression(
        is_compatible=True,
        compatibility_notes="Full benchmark coverage match",
        pass_rate_delta=0.0,
        avg_latency_ms_delta=0.0,
        p95_latency_ms_delta=0.0,
        errored_cases_delta=2,
        newly_failing_count=0,
        newly_fixed_count=0,
        thresholds=thresholds,
        is_all_mock=False,
    )
    assert status_at == "regressed"
    assert any("Execution error count increased by 2 (threshold: 2)" in r for r in reasons_at)

    # 3. Above threshold (3 new errors)
    status_above, reasons_above = ComparisonService.classify_regression(
        is_compatible=True,
        compatibility_notes="Full benchmark coverage match",
        pass_rate_delta=0.0,
        avg_latency_ms_delta=0.0,
        p95_latency_ms_delta=0.0,
        errored_cases_delta=3,
        newly_failing_count=0,
        newly_fixed_count=0,
        thresholds=thresholds,
        is_all_mock=False,
    )
    assert status_above == "regressed"
    assert any("Execution error count increased by 3 (threshold: 2)" in r for r in reasons_above)


def test_coverage_discrepancy_explicitly_documented(client: TestClient, db_session: Session):
    """
    Verifies that runs with differing test case coverage are explicitly reported
    with differing denominators and cannot silently appear equivalent to identical coverage.
    """
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)

    base_cases = [
        {"case_identifier": "c1", "status": "passed"},
        {"case_identifier": "c2", "status": "passed"},
        {"case_identifier": "c3", "status": "passed"},
    ]
    # Candidate only evaluated 2 cases (c3 is missing)
    cand_cases = [
        {"case_identifier": "c1", "status": "passed"},
        {"case_identifier": "c2", "status": "passed"},
    ]

    base_run = create_mock_run(db_session, dataset, agent, case_results=base_cases)
    cand_run = create_mock_run(db_session, dataset, agent, case_results=cand_cases)

    res = client.post(
        "/api/v1/comparisons",
        json={"candidate_run_id": cand_run.id, "baseline_run_id": base_run.id},
    )
    assert res.status_code == 201
    data = res.json()
    assert "Partial coverage match" in data["compatibility_notes"]
    assert "1 cases missing in candidate" in data["compatibility_notes"]
    assert any("Coverage notice:" in r for r in data["reasons"])
    assert any("metric denominators differ" in r for r in data["reasons"])


def test_baseline_and_comparison_persistence_across_sessions(client: TestClient, db_session: Session):
    """
    Verifies that baseline assignment and comparison results are persistently saved in the database
    and can be retrieved cleanly as immutable records.
    """
    agent = create_agent(db_session)
    dataset = create_dataset(db_session)
    cases = [{"case_identifier": "c1", "status": "passed"}]

    base_run = create_mock_run(db_session, dataset, agent, name="Persistent Base", case_results=cases)
    cand_run = create_mock_run(db_session, dataset, agent, name="Persistent Cand", case_results=cases)

    # Set baseline
    base_put = client.put("/api/v1/baselines", json={"dataset_id": dataset.id, "run_id": base_run.id, "notes": "Persistent Baseline"})
    assert base_put.status_code == 200

    # Retrieve baseline
    base_get = client.get(f"/api/v1/baselines/{dataset.id}")
    assert base_get.status_code == 200
    assert base_get.json()["run_id"] == base_run.id
    assert base_get.json()["notes"] == "Persistent Baseline"

    # Compare
    comp_post = client.post("/api/v1/comparisons", json={"candidate_run_id": cand_run.id, "baseline_run_id": base_run.id})
    assert comp_post.status_code == 201
    comp_id = comp_post.json()["id"]

    # Retrieve saved comparison
    comp_get = client.get(f"/api/v1/comparisons/{comp_id}")
    assert comp_get.status_code == 200
    assert comp_get.json()["id"] == comp_id
    assert comp_get.json()["baseline_run_id"] == base_run.id
    assert comp_get.json()["candidate_run_id"] == cand_run.id
    assert len(comp_get.json()["case_comparisons"]) == 1


def test_get_nonexistent_comparison_returns_404(client: TestClient):
    """Verifies that requesting an invalid or nonexistent comparison returns HTTP 404."""
    res = client.get("/api/v1/comparisons/non-existent-comp-id")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    # Also verify regressions sub-endpoint returns 404
    res_reg = client.get("/api/v1/comparisons/non-existent-comp-id/regressions")
    assert res_reg.status_code == 404


def test_get_nonexistent_baseline_returns_404(client: TestClient):
    """Verifies that requesting an active baseline for an unknown dataset returns HTTP 404."""
    res = client.get("/api/v1/baselines/non-existent-dataset-id")
    assert res.status_code == 404
    assert "no active baseline found" in res.json()["detail"].lower()
