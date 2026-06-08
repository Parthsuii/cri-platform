from __future__ import annotations

from pydantic import BaseModel, Field

class CRIAction(BaseModel):
    action_id: str = Field(description="Unique action execution identifier")
    agent_id: str = Field(description="Identifier of the executing agent")
    trace_id: str = Field(description="Correlation identifier for tracing execution lineage")
    action_type: str = Field(description="Type/command category of the action")
    payload: dict = Field(default_factory=dict, description="Input parameters and environment metadata")
    metadata: dict = Field(default_factory=dict, description="Custom action metadata context")
