from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RegressionThresholds(BaseModel):
    """
    Configurable regression detection thresholds with documented units and default values.
    """
    pass_rate_decline_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Decline in pass rate (in percentage points) to classify as a regression. Default 0.0 pp.",
    )
    latency_increase_threshold_ms: float = Field(
        default=100.0,
        ge=0.0,
        description="Increase in average latency (in milliseconds) to classify as a latency regression. Default 100.0 ms.",
    )
    p95_latency_increase_threshold_ms: float = Field(
        default=150.0,
        ge=0.0,
        description="Increase in p95 latency (in milliseconds) to classify as a latency regression. Default 150.0 ms.",
    )
    error_count_increase_threshold: int = Field(
        default=1,
        ge=1,
        description="Threshold of new execution errors to classify as an error regression. Default 1 error.",
    )
    pass_rate_improvement_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Improvement in pass rate (in percentage points) to classify as an improvement. Default 0.0 pp.",
    )


class CaseComparisonResult(BaseModel):
    """
    Per-case comparison outcome between baseline run and candidate run.
    """
    case_identifier: str = Field(..., description="Stable test case identifier")
    input_prompt: str = Field(..., description="Input prompt provided to agent")
    expected_output: Optional[str] = Field(default=None, description="Expected reference output")
    baseline_status: Optional[str] = Field(default=None, description="Status in baseline ('passed', 'failed', 'error', 'unscored', None if absent)")
    candidate_status: Optional[str] = Field(default=None, description="Status in candidate ('passed', 'failed', 'error', 'unscored', None if absent)")
    baseline_score: Optional[float] = Field(default=None, description="Score in baseline run (0.0 to 1.0)")
    candidate_score: Optional[float] = Field(default=None, description="Score in candidate run (0.0 to 1.0)")
    scoring_method: Optional[str] = Field(default=None, description="Scoring rule applied to this case")
    outcome_change: str = Field(
        ...,
        description=(
            "Classification of case outcome change: 'newly_failing', 'fixed', "
            "'newly_errored', 'newly_unscored', 'persistent_failure', 'persistent_pass', "
            "'added', 'removed', 'unchanged'"
        ),
    )
    baseline_latency_ms: Optional[float] = Field(default=None, description="Baseline measured latency in ms")
    candidate_latency_ms: Optional[float] = Field(default=None, description="Candidate measured latency in ms")
    latency_delta_ms: Optional[float] = Field(default=None, description="Candidate latency minus baseline latency in ms")
    baseline_output: Optional[str] = Field(default=None, description="Actual output in baseline")
    candidate_output: Optional[str] = Field(default=None, description="Actual output in candidate")


class EvaluationComparisonCreate(BaseModel):
    candidate_run_id: str = Field(..., description="ID of the candidate evaluation run to evaluate")
    baseline_run_id: Optional[str] = Field(
        default=None,
        description="Optional baseline run ID. If omitted, uses the active baseline designated for the dataset.",
    )
    thresholds: Optional[RegressionThresholds] = Field(
        default=None,
        description="Optional custom regression thresholds for this comparison",
    )


class EvaluationComparisonRead(BaseModel):
    id: str = Field(..., description="Unique comparison identifier")
    dataset_id: str = Field(..., description="Benchmark dataset ID")
    baseline_run_id: str = Field(..., description="Baseline evaluation run ID")
    candidate_run_id: str = Field(..., description="Candidate evaluation run ID")
    status: str = Field(
        ...,
        description="Overall classification: 'improved', 'regressed', 'unchanged', 'mixed', 'inconclusive'",
    )
    is_compatible: bool = Field(default=True, description="Whether the compared runs had compatible benchmark coverage")
    compatibility_notes: Optional[str] = Field(default=None, description="Details on dataset and coverage compatibility")

    # Metric Deltas
    pass_rate_delta: Optional[float] = Field(
        default=None,
        description="Candidate pass rate minus baseline pass rate in percentage points (e.g. +5.0 pp, -10.0 pp)",
    )
    accuracy_delta: Optional[float] = Field(
        default=None,
        description="Candidate accuracy minus baseline accuracy in percentage points",
    )
    passed_cases_delta: int = Field(default=0, description="Candidate passed cases minus baseline passed cases")
    failed_cases_delta: int = Field(default=0, description="Candidate failed cases minus baseline failed cases")
    errored_cases_delta: int = Field(default=0, description="Candidate errored cases minus baseline errored cases")
    unscored_cases_delta: int = Field(default=0, description="Candidate unscored cases minus baseline unscored cases")
    avg_latency_ms_delta: Optional[float] = Field(
        default=None,
        description="Candidate average latency minus baseline average latency in ms",
    )
    p95_latency_ms_delta: Optional[float] = Field(
        default=None,
        description="Candidate p95 latency minus baseline p95 latency in ms",
    )
    cost_usd_delta: Optional[float] = Field(
        default=None,
        description="Candidate cost minus baseline cost in USD",
    )
    tokens_delta: Optional[int] = Field(
        default=None,
        description="Candidate tokens minus baseline tokens",
    )

    # Per-Case Changes Counts
    newly_failing_count: int = Field(default=0, description="Count of cases that passed in baseline but failed in candidate")
    newly_fixed_count: int = Field(default=0, description="Count of cases that failed in baseline but passed in candidate")
    newly_errored_count: int = Field(default=0, description="Count of cases that newly encountered execution errors")
    newly_unscored_count: int = Field(default=0, description="Count of cases that became unscored")

    total_cases_baseline: int = Field(default=0, description="Total cases executed in baseline run")
    total_cases_candidate: int = Field(default=0, description="Total cases executed in candidate run")

    reasons: List[str] = Field(default_factory=list, description="Documented explanations for regression classification")
    created_at: datetime = Field(..., description="UTC creation timestamp")

    # Convenience metadata attached by service
    baseline_run_name: Optional[str] = Field(default=None, description="Name of baseline run")
    candidate_run_name: Optional[str] = Field(default=None, description="Name of candidate run")
    baseline_agent_name: Optional[str] = Field(default=None, description="Baseline agent name")
    candidate_agent_name: Optional[str] = Field(default=None, description="Candidate agent name")
    baseline_agent_version: Optional[str] = Field(default=None, description="Baseline agent version tag")
    candidate_agent_version: Optional[str] = Field(default=None, description="Candidate agent version tag")
    baseline_pass_rate: Optional[float] = Field(default=None, description="Baseline pass rate in %")
    candidate_pass_rate: Optional[float] = Field(default=None, description="Candidate pass rate in %")
    baseline_avg_latency_ms: Optional[float] = Field(default=None, description="Baseline average latency in ms")
    candidate_avg_latency_ms: Optional[float] = Field(default=None, description="Candidate average latency in ms")

    model_config = ConfigDict(from_attributes=True)


class EvaluationComparisonDetailRead(EvaluationComparisonRead):
    case_comparisons: List[CaseComparisonResult] = Field(
        default_factory=list,
        description="Detailed per-case outcome diffs, latencies, and outputs",
    )
