from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class CRIEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique telemetry event identifier")
    trace_id: str = Field(description="Correlation identifier representing execution lineage")
    agent_id: str = Field(default="generic-agent", description="Identifier of the executing agent")
    event_type: str = Field(description="The semantic category of the lifecycle event (e.g., ACTION_EXECUTED)")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 string timestamp of event generation")
    payload: dict = Field(default_factory=dict, description="Custom event metadata context")

class EventFactory:
    def create(self, trace_id: str, event_type: str, payload: dict | None = None, agent_id: str = "generic-agent") -> CRIEvent:
        if payload and isinstance(payload, dict) and "agent_id" in payload:
            agent_id = payload["agent_id"]
        return CRIEvent(
            trace_id=trace_id,
            event_type=event_type,
            agent_id=agent_id,
            payload=payload or {}
        )
