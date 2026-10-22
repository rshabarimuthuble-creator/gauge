from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.evaluation_run import EvaluationRunRead


class DashboardSummaryResponse(BaseModel):
    datasets_count: int = Field(default=0, description="Total number of evaluation datasets")
    versions_count: int = Field(default=0, description="Total number of registered agent versions")
    total_runs_count: int = Field(default=0, description="Total number of evaluation runs executed")
    latest_run_status: Optional[str] = Field(default=None, description="Status of the most recent evaluation run")
    database_connected: bool = Field(..., description="Whether database is reachable")
    database_message: str = Field(..., description="Database connection status summary")
    recent_runs: List[EvaluationRunRead] = Field(default_factory=list, description="Recent evaluation runs")
