from __future__ import annotations

import time
import uuid
from dataclasses import asdict
from typing import Any, Literal

from .cognition_os import CognitionOperatingSystem
from .events import TraceManager
from .kubernetes import KubernetesExecutionFabric
from .rollback import DistributedRollbackManager
from .runtime import LocalLangGraphRuntime
from .verification import VerificationEngine

TaskMode = Literal["agent", "cognition_os"]


class RuntimeService:
    def __init__(self) -> None:
        self.rollback = DistributedRollbackManager()
        self.tasks: dict[str, dict[str, Any]] = {}

    def submit_task(self, task: str, mode: TaskMode = "cognition_os") -> dict[str, Any]:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        started_at = time.time()
        try:
            if mode == "agent":
                runtime = LocalLangGraphRuntime(trace_manager=TraceManager())
                result: dict[str, Any] = runtime.run(task, active_files=["main.py", "pyproject.toml", "docker-compose.yml"])
                verification = VerificationEngine().verify_execution_history(result["execution_history"])
                checkpoint = self.rollback.create_checkpoint(result, "service task checkpoint")
                response = {
                    "task_id": task_id,
                    "status": "completed",
                    "mode": mode,
                    "task": task,
                    "result": result,
                    "verification": asdict(verification),
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "created_at": started_at,
                    "completed_at": time.time(),
                }
            else:
                cognition_result = CognitionOperatingSystem().run(task)
                checkpoint = self.rollback.create_checkpoint(cognition_result["state"], "service cognition checkpoint")
                response = {
                    "task_id": task_id,
                    "status": "completed",
                    "mode": mode,
                    "task": task,
                    "result": cognition_result,
                    "verification": cognition_result["verification"],
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "created_at": started_at,
                    "completed_at": time.time(),
                }
        except Exception as exc:
            response = {
                "task_id": task_id,
                "status": "failed",
                "mode": mode,
                "task": task,
                "error": str(exc),
                "created_at": started_at,
                "completed_at": time.time(),
            }
        self.tasks[task_id] = response
        return response

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self.tasks.get(task_id)

    def list_tasks(self) -> list[dict[str, Any]]:
        return list(self.tasks.values())

    def replay_trace(self) -> list[dict[str, Any]]:
        return TraceManager().replay()

    def rollback_task(self, checkpoint_id: str) -> dict[str, Any]:
        return {
            "checkpoint_id": checkpoint_id,
            "restored": self.rollback.restore(checkpoint_id),
        }

    def kubernetes_plan(self) -> dict[str, Any]:
        return KubernetesExecutionFabric().plan()
