from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evaluation_result import EvaluationResultRead


class EvaluationRunBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Benchmark run name")
    dataset_id: str = Field(..., description="Target dataset ID")
    agent_version_id: str = Field(..., description="Target agent version ID")


class EvaluationRunCreate(EvaluationRunBase):
    execution_mode: Optional[str] = Field(
        default=None,
        description="Execution mode: 'real' (live LLM API call), 'mock' (deterministic simulation), or None (auto resolution)",
    )
    scoring_config: Optional[str] = Field(
        default=None,
        description="Optional scoring configuration rule (e.g. 'default', 'exact_match', 'normalized_match', 'task_type')",
    )
    background: Optional[bool] = Field(
        default=False,
        description="Optional flag to execute evaluation asynchronously in background",
    )



class EvaluationRunRead(EvaluationRunBase):
    id: str = Field(..., description="Unique run identifier")
    status: str = Field(..., description="Run status: 'pending', 'running', 'completed', 'failed', 'cancelled'")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    # Snapshot and Provenance
    dataset_version: Optional[str] = Field(default=None, description="Version of the dataset captured at execution time")
    dataset_snapshot_json: Optional[str] = Field(default=None, description="Immutable JSON snapshot of evaluated test cases")
    scoring_config: Optional[str] = Field(default=None, description="Scoring configuration applied to this run")
    model_provider: Optional[str] = Field(default=None, description="Agent model provider (e.g. 'groq', 'openai', 'mock')")
    model_name: Optional[str] = Field(default=None, description="Model identifier used for inference")

    # Aggregate Metrics
    total_cases: int = Field(default=0, description="Total number of executed test cases (N_run)")
    passed_cases: int = Field(default=0, description="Number of passed test cases meeting scoring criteria")
    failed_cases: int = Field(default=0, description="Number of failed test cases")
    errored_cases: int = Field(default=0, description="Number of test cases encountering adapter/provider errors")
    unscored_cases: int = Field(default=0, description="Number of test cases missing required reference output")
    pass_rate: Optional[float] = Field(
        default=None,
        description="Percentage pass rate: (passed / (passed + failed)) * 100. Unscored and errored cases are excluded from the eligible denominator.",
    )
    accuracy: Optional[float] = Field(
        default=None,
        description="Strict accuracy: (passed / total_cases) * 100. Execution errors reduce accuracy.",
    )
    error_rate: Optional[float] = Field(
        default=None,
        description="Error rate: (errored_cases / total_cases) * 100.",
    )
    dataset_coverage: Optional[float] = Field(
        default=None,
        description="Dataset coverage: (total_cases / dataset_total_cases) * 100.",
    )
    avg_latency_ms: Optional[float] = Field(default=None, description="Average execution latency in milliseconds")
    min_latency_ms: Optional[float] = Field(default=None, description="Minimum execution latency in milliseconds")
    max_latency_ms: Optional[float] = Field(default=None, description="Maximum execution latency in milliseconds")
    p95_latency_ms: Optional[float] = Field(default=None, description="95th percentile execution latency in milliseconds")

    # Token and Cost Telemetry
    total_cost_usd: Optional[float] = Field(default=None, description="Total reliable inference cost in USD, or None if pricing is unknown")
    total_tokens: Optional[int] = Field(default=None, description="Total tokens consumed across all cases")
    prompt_tokens: Optional[int] = Field(default=None, description="Total prompt tokens consumed")
    completion_tokens: Optional[int] = Field(default=None, description="Total completion tokens generated")

    error_message: Optional[str] = Field(default=None, description="Error details if the run failed fatally")

    model_config = ConfigDict(from_attributes=True)


class EvaluationRunDetailRead(EvaluationRunRead):
    results: List[EvaluationResultRead] = Field(
        default_factory=list,
        description="Persisted individual test case execution results",
    )
