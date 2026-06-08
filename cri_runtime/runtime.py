from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Callable

from .classifiers import classify_shell
from .events import EventFactory, TraceManager
from .io import read_file, run_shell
from .policy import PolicyEngine
from .sandbox import SandboxPoolManager
from .state import AgentState, build_state, semantic_state_hash


@dataclass(frozen=True)
class PlanStep:
    name: str
    tool: str
    input: str


@dataclass(frozen=True)
class ExecutionRecord:
    step: str
    tool: str
    attempt: int
    status: str
    output: dict[str, Any]
    latency_ms: int
    timestamp: float


class PlannerNode:
    def plan(self, task: str) -> list[PlanStep]:
        lowered = task.lower()
        if lowered.startswith("read "):
            return [PlanStep(name="read_requested_file", tool="read_file", input=task[5:].strip())]
        if lowered.startswith("run "):
            return [PlanStep(name="run_requested_command", tool="shell", input=task[4:].strip())]
        return [
            PlanStep(name="classify_task", tool="classify_shell", input=task),
            PlanStep(name="summarize_runtime_state", tool="state_hash", input=task),
        ]


class ToolExecutionLayer:
    def __init__(self, sandbox_manager: SandboxPoolManager | None = None, policy_engine: PolicyEngine | None = None) -> None:
        self.sandbox_manager = sandbox_manager or SandboxPoolManager()
        self.policy_engine = policy_engine or PolicyEngine()
        self.tools: dict[str, Callable[[str, AgentState], dict[str, Any]]] = {
            "read_file": self._read_file,
            "shell": self._shell,
            "classify_shell": self._classify_shell,
            "state_hash": self._state_hash,
        }

    def execute(self, step: PlanStep, state: AgentState) -> dict[str, Any]:
        if step.tool not in self.tools:
            raise KeyError(f"unknown tool: {step.tool}")
        return self.tools[step.tool](step.input, state)

    def _read_file(self, path: str, _state: AgentState) -> dict[str, Any]:
        return {"path": path, "content": read_file(path)}

    def _shell(self, command: str, _state: AgentState) -> dict[str, Any]:
        classification = classify_shell(command)
        decision = self.policy_engine.evaluate("shell", {"classification": classification})
        if not decision.allowed:
            return {"route": "blocked", "classification": classification, "policy": decision.reason}
        if classification["risk"] == "HIGH":
            claim = self.sandbox_manager.claim()
            result = self.sandbox_manager.exec_in_sandbox(claim, command)
            return {"route": "sandbox", "classification": classification, "policy": decision.reason, "result": result}
        return {"route": "direct", "classification": classification, "policy": decision.reason, "result": run_shell(command)}

    def _classify_shell(self, command: str, _state: AgentState) -> dict[str, Any]:
        return classify_shell(command)

    def _state_hash(self, _task: str, state: AgentState) -> dict[str, Any]:
        return {"semantic_state_hash": semantic_state_hash(state)}


class RetrySystem:
    def __init__(self, max_attempts: int = 2) -> None:
        self.max_attempts = max_attempts

    def run(self, step: PlanStep, state: AgentState, tools: ToolExecutionLayer) -> ExecutionRecord:
        last_error: str | None = None
        for attempt in range(1, self.max_attempts + 1):
            started = time.time()
            try:
                output = tools.execute(step, state)
                return ExecutionRecord(
                    step=step.name,
                    tool=step.tool,
                    attempt=attempt,
                    status="ok",
                    output=output,
                    latency_ms=int((time.time() - started) * 1000),
                    timestamp=time.time(),
                )
            except Exception as exc:
                last_error = str(exc)
                state["retries"] += 1
        return ExecutionRecord(
            step=step.name,
            tool=step.tool,
            attempt=self.max_attempts,
            status="failed",
            output={"error": last_error or "unknown error"},
            latency_ms=0,
            timestamp=time.time(),
        )


class LocalLangGraphRuntime:
    """Small LangGraph-style state runner used until the external package is added."""

    def __init__(
        self,
        planner: PlannerNode | None = None,
        tools: ToolExecutionLayer | None = None,
        retry_system: RetrySystem | None = None,
        trace_manager: TraceManager | None = None,
    ) -> None:
        self.planner = planner or PlannerNode()
        self.tools = tools or ToolExecutionLayer()
        self.retry_system = retry_system or RetrySystem()
        self.trace_manager = trace_manager
        self.event_factory = EventFactory()

    def run(self, task: str, active_files: list[str] | None = None) -> AgentState:
        state = build_state(task, active_files or ["main.py", "pyproject.toml"])
        steps = self.planner.plan(task)
        self._trace("plan_created", {"task": task, "steps": [asdict(step) for step in steps]})
        for step in steps:
            record = self.retry_system.run(step, state, self.tools)
            state["execution_history"].append(asdict(record))
            self._trace("step_executed", asdict(record))
        self._trace("run_completed", {"semantic_state_hash": semantic_state_hash(state), "retries": state["retries"]})
        return state

    def _trace(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.trace_manager is not None:
            self.trace_manager.append(self.event_factory.create(event_type, payload))
