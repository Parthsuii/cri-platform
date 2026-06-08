from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .events import TraceManager
from .kubernetes import KubernetesExecutionFabric
from .multi_agent import MultiAgentRuntime
from .policy import ContradictionDetector
from .rollback import DistributedRollbackManager
from .runtime import LocalLangGraphRuntime
from .verification import VerificationEngine


class CognitionOperatingSystem:
    def __init__(self) -> None:
        self.trace_manager = TraceManager()
        self.runtime = LocalLangGraphRuntime(trace_manager=self.trace_manager)
        self.multi_agent = MultiAgentRuntime()
        self.rollback = DistributedRollbackManager()
        self.verifier = VerificationEngine()
        self.contradictions = ContradictionDetector()
        self.fabric = KubernetesExecutionFabric()

    def run(self, task: str) -> dict[str, Any]:
        state = self.runtime.run(task, active_files=["main.py", "pyproject.toml", "docker-compose.yml"])
        checkpoint = self.rollback.create_checkpoint(state, "post-runtime execution checkpoint")
        verification = self.verifier.verify_execution_history(state["execution_history"])
        replayed_events = self.trace_manager.replay()
        findings = self.contradictions.detect(replayed_events)
        return {
            "task": task,
            "state": state,
            "checkpoint": asdict(checkpoint),
            "verification": asdict(verification),
            "contradictions": findings,
            "kubernetes": self.fabric.plan(),
        }
