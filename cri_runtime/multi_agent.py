from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .runtime import LocalLangGraphRuntime
from .verification import VerificationEngine


@dataclass(frozen=True)
class AgentResult:
    name: str
    state: dict[str, Any]


class MultiAgentRuntime:
    def __init__(self) -> None:
        self.runtime = LocalLangGraphRuntime()
        self.verifier = VerificationEngine()

    def run(self, task: str) -> dict[str, Any]:
        executor_state = self.runtime.run(task)
        verification = self.verifier.verify_execution_history(executor_state["execution_history"])
        return {
            "agents": [
                asdict(AgentResult("executor", executor_state)),
                asdict(AgentResult("verifier", {"verification": asdict(verification)})),
            ]
        }
