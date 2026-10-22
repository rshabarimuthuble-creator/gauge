import pytest
from app.services.evaluator import (
    score_exact_match,
    score_normalized_match,
    score_structured_output,
    score_partial_credit,
    score_case_execution,
    compute_aggregate_metrics,
    CaseEvaluation,
)
from app.services.adapters.base import AgentExecutionResult


def test_exact_match_scoring():
    # Strict equality after whitespace strip
    passed, score, expl = score_exact_match("Paris", "Paris")
    assert passed is True
    assert score == 1.0
    assert expl is None

    passed, score, expl = score_exact_match("  Paris \n", "Paris")
    assert passed is True
    assert score == 1.0

    passed, score, expl = score_exact_match("paris", "Paris")
    assert passed is False
    assert score == 0.0
    assert "Exact string mismatch" in expl


def test_normalized_match_scoring_casing_and_punctuation():
    # Case insensitivity and punctuation tolerance
    passed, score, _ = score_normalized_match("paris.", "Paris")
    assert passed is True
    assert score == 1.0

    passed, score, _ = score_normalized_match("\"CANBERRA!\"", "Canberra")
    assert passed is True
    assert score == 1.0

    passed, score, _ = score_normalized_match("  Multiple   spaces  here. ", "multiple spaces here")
    assert passed is True
    assert score == 1.0


def test_normalized_match_scoring_numeric_and_currency():
    # Numeric equivalence: 42 == 42.0
    passed, score, _ = score_normalized_match("42.0", "42")
    assert passed is True
    assert score == 1.0

    # Currency stripping: $12.00 == 12 == $12
    passed, score, _ = score_normalized_match("$12.00", "$12")
    assert passed is True
    assert score == 1.0

    passed, score, _ = score_normalized_match("12", "$12")
    assert passed is True
    assert score == 1.0

    # Percentage parsing: 50% == 0.5
    passed, score, _ = score_normalized_match("50%", "0.5")
    assert passed is True
    assert score == 1.0

    # Non-matching numbers
    passed, score, expl = score_normalized_match("43", "42")
    assert passed is False
    assert score == 0.0
    assert "Normalized mismatch" in expl


def test_normalized_match_boolean_equivalence():
    passed, score, _ = score_normalized_match("Yes", "true")
    assert passed is True
    assert score == 1.0

    passed, score, _ = score_normalized_match("0", "false")
    assert passed is True
    assert score == 1.0

    passed, score, _ = score_normalized_match("no", "true")
    assert passed is False
    assert score == 0.0


def test_structured_output_json_scoring():
    # Valid JSON matching
    exp = '{"username": "Alex", "age": 29}'
    act = '{"age": 29, "username": "Alex"}'
    passed, score, _ = score_structured_output(act, exp)
    assert passed is True
    assert score == 1.0

    # Markdown code block extraction
    act_md = '```json\n{"username": "Alex", "age": 29}\n```'
    passed, score, _ = score_structured_output(act_md, exp)
    assert passed is True
    assert score == 1.0

    # Invalid JSON fails
    act_malformed = '{"username": Alex, age: 29}'
    passed, score, expl = score_structured_output(act_malformed, exp)
    assert passed is False
    assert score == 0.0
    assert "Output is not valid JSON" in expl

    # Key / value mismatch
    act_diff = '{"username": "Alex", "age": 30}'
    passed, score, expl = score_structured_output(act_diff, exp)
    assert passed is False
    assert score == 0.0
    assert "Structured JSON mismatch" in expl


def test_structured_output_subset_mode():
    exp = '{"origin": "SFO", "destination": "JFK"}'
    act_superset = '{"origin": "SFO", "destination": "JFK", "flight_num": 102, "status": "on_time"}'
    passed, score, _ = score_structured_output(act_superset, exp, criteria="subset match allowed")
    assert passed is True
    assert score == 1.0

    act_missing = '{"origin": "SFO"}'
    passed, score, expl = score_structured_output(act_missing, exp, criteria="subset")
    assert passed is False
    assert score == 0.0
    assert "Missing key 'destination'" in expl


def test_partial_credit_scoring():
    exp = "red, green, blue"
    act_full = "The primary colors are red, green, and blue."
    passed, score, expl = score_partial_credit(act_full, exp, metadata={"pass_threshold": 0.67})
    assert passed is True
    assert score == 1.0
    assert "3/3 items matched" in expl

    # Partial match: 2 out of 3 (67%) passes 0.67 threshold
    act_partial = "I only remember red and green."
    passed, score, expl = score_partial_credit(act_partial, exp, metadata={"pass_threshold": 0.67})
    assert passed is True
    assert score == 0.67
    assert "2/3 items matched" in expl

    # Below threshold: 1 out of 3 (33%) fails 0.67 threshold
    act_low = "Only red."
    passed, score, expl = score_partial_credit(act_low, exp, metadata={"pass_threshold": 0.67})
    assert passed is False
    assert score == 0.33
    assert "1/3 items matched" in expl


def test_errors_and_unscored_never_counted_as_passed():
    # Error execution
    exec_err = AgentExecutionResult(
        output="I know the answer!",
        latency_ms=10.0,
        token_usage=0,
        tokens_estimated=True,
        is_mock=True,
        is_error=True,
        error_message="Connection timed out",
    )
    res = score_case_execution("I know the answer!", exec_err)
    assert res.status == "error"
    assert res.score == 0.0
    assert res.error_message == "Connection timed out"

    # Unscored execution (empty expected output)
    exec_norm = AgentExecutionResult(
        output="Deep philosophical thoughts",
        latency_ms=10.0,
        token_usage=10,
        tokens_estimated=True,
        is_mock=True,
        is_error=False,
    )
    res_unscored = score_case_execution("", exec_norm)
    assert res_unscored.status == "unscored"
    assert res_unscored.score is None


def test_metrics_distinguish_accuracy_pass_rate_error_rate_and_coverage():
    # 10 test cases:
    # 6 passed, 2 failed, 1 errored, 1 unscored
    evals = [
        CaseEvaluation(status="passed", actual_output="A", expected_output="A", score=1.0, scoring_method="exact_match", latency_ms=10.0, token_usage=5, prompt_tokens=2, completion_tokens=3, tokens_estimated=True, is_mock=True, cost_usd=None, model_provider="mock", model_name="m", error_message=None, metadata_json=None)
        for _ in range(6)
    ]
    evals += [
        CaseEvaluation(status="failed", actual_output="B", expected_output="A", score=0.0, scoring_method="exact_match", latency_ms=10.0, token_usage=5, prompt_tokens=2, completion_tokens=3, tokens_estimated=True, is_mock=True, cost_usd=None, model_provider="mock", model_name="m", error_message=None, metadata_json=None)
        for _ in range(2)
    ]
    evals.append(
        CaseEvaluation(status="error", actual_output=None, expected_output="A", score=0.0, scoring_method="exact_match", latency_ms=0.0, token_usage=0, prompt_tokens=0, completion_tokens=0, tokens_estimated=True, is_mock=True, cost_usd=None, model_provider="mock", model_name="m", error_message="Failed", metadata_json=None)
    )
    evals.append(
        CaseEvaluation(status="unscored", actual_output="Open", expected_output="", score=None, scoring_method="unscored", latency_ms=5.0, token_usage=5, prompt_tokens=2, completion_tokens=3, tokens_estimated=True, is_mock=True, cost_usd=None, model_provider="mock", model_name="m", error_message=None, metadata_json=None)
    )

    metrics = compute_aggregate_metrics(evals, dataset_total_cases=12)

    assert metrics["total_cases"] == 10
    assert metrics["passed_cases"] == 6
    assert metrics["failed_cases"] == 2
    assert metrics["errored_cases"] == 1
    assert metrics["unscored_cases"] == 1
    assert metrics["eligible_cases"] == 8

    # Pass Rate: 6 / (6 + 2) = 6/8 = 75.0%
    assert metrics["pass_rate"] == 75.0

    # Accuracy: 6 / 10 = 60.0%
    assert metrics["accuracy"] == 60.0

    # Error Rate: 1 / 10 = 10.0%
    assert metrics["error_rate"] == 10.0

    # Dataset Coverage: 10 / 12 = 83.33%
    assert metrics["dataset_coverage"] == 83.33
