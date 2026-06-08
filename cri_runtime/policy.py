from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    tags: list[str] = field(default_factory=list)


class PolicyEngine:
    def __init__(self, denied_tools: set[str] | None = None) -> None:
        self.denied_tools = denied_tools or set()

    def evaluate(self, tool: str, payload: dict[str, Any]) -> PolicyDecision:
        if tool in self.denied_tools:
            return PolicyDecision(False, f"tool denied by policy: {tool}", ["policy_denied"])
        if payload.get("classification", {}).get("risk") == "HIGH":
            return PolicyDecision(True, "allowed with sandbox routing", ["sandbox_required"])
        return PolicyDecision(True, "allowed", [])


class ContradictionDetector:
    def detect(self, events: list[dict[str, Any]]) -> list[str]:
        findings: list[str] = []
        completed = any(event.get("event_type") == "run_completed" for event in events)
        failed_steps = [
            event
            for event in events
            if event.get("event_type") == "step_executed" and event.get("payload", {}).get("status") == "failed"
        ]
        if completed and failed_steps:
            findings.append("run_completed emitted even though one or more steps failed")
        return findings
