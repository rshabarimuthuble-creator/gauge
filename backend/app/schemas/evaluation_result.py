from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EvaluationResultRead(BaseModel):
    id: str = Field(..., description="Unique result identifier")
    run_id: str = Field(..., description="Evaluation run ID")
    test_case_id: Optional[str] = Field(default=None, description="Linked test case ID, if applicable")
    case_identifier: str = Field(..., description="Stable test case identifier")
    input_prompt: str = Field(..., description="Input prompt provided to agent")
    expected_output: Optional[str] = Field(default=None, description="Expected reference output")
    actual_output: Optional[str] = Field(default=None, description="Actual output returned by agent")
    status: str = Field(..., description="Result status: 'passed', 'failed', 'error', 'unscored'")
    score: Optional[float] = Field(default=None, description="Numeric evaluation score between 0.0 and 1.0 (None if unscored)")
    scoring_method: Optional[str] = Field(default="exact_match", description="Scoring rule applied (e.g. 'exact_match', 'normalized_match', 'structured_output', 'partial_credit')")
    latency_ms: Optional[float] = Field(default=None, description="Measured execution latency in milliseconds")
    token_usage: Optional[int] = Field(default=None, description="Reported or estimated token usage")
    prompt_tokens: Optional[int] = Field(default=None, description="Input prompt token count")
    completion_tokens: Optional[int] = Field(default=None, description="Generated output token count")
    tokens_estimated: bool = Field(default=True, description="Whether token count is an estimate vs. measured")
    cost_usd: Optional[float] = Field(default=None, description="Calculated inference cost in USD, or None if pricing is unknown")
    model_provider: Optional[str] = Field(default=None, description="LLM provider name (e.g. 'groq', 'openai', 'mock')")
    model_name: Optional[str] = Field(default=None, description="Model identifier used for this case")
    error_message: Optional[str] = Field(default=None, description="Execution error detail, if status is error")
    is_mock: bool = Field(default=True, description="Whether execution was performed by a mock adapter")
    metadata_json: Optional[str] = Field(default=None, description="Diagnostic and execution metadata")
    created_at: datetime = Field(..., description="UTC creation timestamp")

    model_config = ConfigDict(from_attributes=True)
