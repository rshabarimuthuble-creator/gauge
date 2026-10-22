from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EvaluationBaselineCreate(BaseModel):
    dataset_id: str = Field(..., description="ID of the benchmark dataset")
    run_id: str = Field(..., description="ID of the completed evaluation run to designate as baseline")
    notes: Optional[str] = Field(default=None, max_length=500, description="Optional notes on why this run is the baseline")


class EvaluationBaselineRead(BaseModel):
    id: str = Field(..., description="Unique baseline record identifier")
    dataset_id: str = Field(..., description="Target dataset identifier")
    run_id: str = Field(..., description="Active baseline evaluation run identifier")
    agent_version_id: str = Field(..., description="Agent version identifier used in baseline run")
    is_active: bool = Field(default=True, description="Whether this is the currently active baseline")
    notes: Optional[str] = Field(default=None, description="Baseline notes or tags")
    created_at: datetime = Field(..., description="UTC creation timestamp")
    updated_at: datetime = Field(..., description="UTC update timestamp")

    # Convenience metadata attached by service
    run_name: Optional[str] = Field(default=None, description="Name of the baseline evaluation run")
    agent_name: Optional[str] = Field(default=None, description="Agent name used in baseline")
    agent_version: Optional[str] = Field(default=None, description="Agent version tag used in baseline")
    pass_rate: Optional[float] = Field(default=None, description="Pass rate of baseline run in %")

    model_config = ConfigDict(from_attributes=True)
