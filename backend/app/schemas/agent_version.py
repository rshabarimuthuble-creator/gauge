from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AgentVersionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Agent or prompt name")
    version: str = Field(..., min_length=1, max_length=64, description="Version tag, e.g. v1.0.0 or experiment-1")
    model_provider: str = Field(..., min_length=1, max_length=64, description="Provider (e.g. openai, anthropic, google)")
    model_name: str = Field(..., min_length=1, max_length=128, description="Exact model ID (e.g. gpt-4o, claude-3-5-sonnet)")
    prompt_text: Optional[str] = Field(default=None, description="System prompt or template definition")


class AgentVersionCreate(AgentVersionBase):
    pass


class AgentVersionRead(AgentVersionBase):
    id: str = Field(..., description="Unique agent version identifier")
    created_at: datetime = Field(..., description="UTC creation timestamp")

    model_config = ConfigDict(from_attributes=True)
