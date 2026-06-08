from __future__ import annotations

from typing import Any, Protocol
from packages.contracts.action import CRIAction

class Adapter(Protocol):
    def normalize(self, action: dict[str, Any]) -> CRIAction:
        ...

class GenericAdapter:
    def normalize(self, action: dict[str, Any]) -> CRIAction:
        import uuid
        action_id = str(action.get("action_id", action.get("id", f"act-{uuid.uuid4().hex[:12]}")))
        agent_id = str(action.get("agent_id", action.get("agent", "generic-agent")))
        trace_id = str(action.get("trace_id", action.get("trace", f"trace-{uuid.uuid4().hex[:12]}")))
        action_type = str(action.get("action_type", action.get("type", "run_command")))
        payload = dict(action.get("payload", action.get("input", action)))
        metadata = dict(action.get("metadata", {}))
        
        return CRIAction(
            action_id=action_id,
            agent_id=agent_id,
            trace_id=trace_id,
            action_type=action_type,
            payload=payload,
            metadata=metadata
        )
