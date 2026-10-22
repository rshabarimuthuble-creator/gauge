from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class EvaluationTestCaseBase(BaseModel):
    case_identifier: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Stable case identifier, e.g. case-1, GAUGE-MATH-01, or gsm8k-001",
    )
    input_prompt: str = Field(
        ...,
        min_length=1,
        description="Prompt or problem text passed to the agent",
    )
    expected_output: Optional[str] = Field(
        default=None,
        description="Expected reference response for scoring correctness",
    )
    criteria: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional evaluation criteria, rubric, or scoring notes",
    )
    category: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Task category, e.g. mathematics, logic, structured_json, knowledge",
    )
    difficulty: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Difficulty level: easy, medium, hard",
    )
    scoring_method: Optional[str] = Field(
        default="exact_match",
        max_length=64,
        description="Preferred scoring method: exact_match, normalized_match, structured_output, partial_credit",
    )
    metadata_json: Optional[str] = Field(
        default=None,
        description="Optional serialized JSON metadata (e.g. provenance, tags, rubric)",
    )


class EvaluationTestCaseCreate(EvaluationTestCaseBase):
    pass


class EvaluationTestCaseRead(EvaluationTestCaseBase):
    id: str = Field(..., description="Unique test case identifier")
    dataset_id: str = Field(..., description="Parent dataset identifier")
    case_identifier: str = Field(..., description="Resolved case identifier")
    created_at: datetime = Field(..., description="UTC creation timestamp")

    model_config = ConfigDict(from_attributes=True)
