from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.test_case import EvaluationTestCaseCreate, EvaluationTestCaseRead


class EvaluationDatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Dataset title or benchmark name")
    description: Optional[str] = Field(default=None, max_length=2000, description="Overview of dataset content")
    version: str = Field(default="v1.0.0", max_length=32, description="Semantic version of the dataset benchmark")


class EvaluationDatasetCreate(EvaluationDatasetBase):
    test_cases: Optional[List[EvaluationTestCaseCreate]] = Field(
        default=None,
        description="Optional list of benchmark test cases to create with the dataset",
    )


class EvaluationDatasetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=2000)
    version: Optional[str] = Field(default=None, max_length=32)


class EvaluationDatasetRead(EvaluationDatasetBase):
    id: str = Field(..., description="Unique dataset identifier")
    created_at: datetime = Field(..., description="UTC creation timestamp")
    updated_at: datetime = Field(..., description="UTC update timestamp")
    test_cases_count: int = Field(default=0, description="Total number of test cases in dataset")
    test_cases: Optional[List[EvaluationTestCaseRead]] = Field(
        default=None,
        description="List of test cases (included in detailed dataset fetch)",
    )

    model_config = ConfigDict(from_attributes=True)
