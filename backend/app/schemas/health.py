from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class DBHealthStatus(BaseModel):
    connected: bool = Field(..., description="Whether the database is reachable")
    message: str = Field(..., description="Status message or error summary")
    dialect: Optional[str] = Field(default=None, description="Database dialect (e.g. postgresql, sqlite)")


class LLMProviderStatus(BaseModel):
    provider: str = Field(..., description="Active or configured LLM provider name")
    model: str = Field(..., description="Configured default model identifier")
    api_key_configured: bool = Field(..., description="Whether a valid provider API key is present in environment")
    default_execution_mode: str = Field(default="auto", description="Default execution mode ('auto', 'real', 'mock')")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Application operational status ('ok', 'degraded', 'unhealthy')")
    service: str = Field(default="gauge-backend", description="Service identifier")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
    database: DBHealthStatus = Field(..., description="Database connection health details")
    llm_provider: Optional[LLMProviderStatus] = Field(default=None, description="LLM provider configuration status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the health check"
    )
