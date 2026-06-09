from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar
from .classifiers import classify_shell

T = TypeVar("T")

@dataclass(frozen=True)
class Checkpoint:
    action_name: str
    decision: str
    risk: str
    findings: list[str] = field(default_factory=list)

class CheckpointStore:
    def __init__(self) -> None:
        self._checkpoints: list[Checkpoint] = []

    def add(self, checkpoint: Checkpoint) -> None:
        self._checkpoints.append(checkpoint)

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "action_name": checkpoint.action_name,
                "decision": checkpoint.decision,
                "risk": checkpoint.risk,
                "findings": checkpoint.findings,
            }
            for checkpoint in self._checkpoints
        ]

class ExecutionRouter:
    def route_shell(self, command: str) -> dict[str, Any]:
        classification = classify_shell(command)
        route = "sandbox" if classification["risk"] == "HIGH" else "direct"
        return {"route": route, "classification": classification}

class CentralInterceptor:
    def __init__(self, checkpoint_store: CheckpointStore | None = None) -> None:
        self.checkpoint_store = checkpoint_store or CheckpointStore()
        self.router = ExecutionRouter()

    def checkpoint_for(self, action_name: str, args: tuple[object, ...]) -> Checkpoint:
        if action_name in {"run_shell", "sandbox_exec"} and args:
            routed = self.router.route_shell(str(args[0]))
            classification = routed["classification"]
            decision = routed["route"]
            risk = classification["risk"]
            findings = list(classification["findings"])
        else:
            decision = "direct"
            risk = "LOW"
            findings = []

        checkpoint = Checkpoint(action_name=action_name, decision=decision, risk=risk, findings=findings)
        self.checkpoint_store.add(checkpoint)
        return checkpoint

DEFAULT_INTERCEPTOR = CentralInterceptor()

def intercept(action_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapped(*args: object, **kwargs: object) -> T:
            checkpoint = DEFAULT_INTERCEPTOR.checkpoint_for(action_name, args)
            print(f"Intercepted: {action_name} [{checkpoint.decision}/{checkpoint.risk}]")
            return func(*args, **kwargs)
        return wrapped
    return decorator
