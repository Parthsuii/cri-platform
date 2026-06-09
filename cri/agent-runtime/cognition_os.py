from __future__ import annotations

import json
import time
import uuid
from typing import Any

from .memory import MemoryArbitrator
from .governance import ContextGovernorEngine
from cri.belief_engine.store import BeliefStore
from cri.runtime_core.classifiers import ActionClassifier, classify_shell
from cri.checkpoint_engine.dag import CheckpointDAG
from cri.semantic_state.state import AgentState, semantic_state_hash
from cri.rollback_engine.coordinator import RollbackCoordinator


class TaskScheduler:
    """Simple priority FIFO task queue with uncertainty scoring."""
    def __init__(self) -> None:
        self._queue: list[dict[str, Any]] = []

    def enqueue(self, task: str, priority: float = 0.5) -> str:
        task_id = f"cri-task-{uuid.uuid4().hex[:8]}"
        self._queue.append({"id": task_id, "task": task, "priority": priority, "enqueued_at": time.time()})
        self._queue.sort(key=lambda x: x["priority"], reverse=True)
        return task_id

    def dequeue(self) -> dict[str, Any] | None:
        return self._queue.pop(0) if self._queue else None

    def pending(self) -> int:
        return len(self._queue)


class CognitionOS:
    """
    Phase 12 — Cognitive Operating System.

    Acts as the central runtime layer for autonomous AI workloads, combining:
    - Memory Arbitration (episodic + semantic)
    - Context Governance (anti-collapse)
    - Belief Verification (Qdrant)
    - Checkpoint DAG (state lineage)
    - Rollback Coordination
    - Task Scheduling with uncertainty scoring
    - Multi-agent coordination primitives
    """

    def __init__(self) -> None:
        self.scheduler  = TaskScheduler()
        self.memory     = MemoryArbitrator()
        self.governor   = ContextGovernorEngine()
        self.beliefs    = BeliefStore()
        self.dag        = CheckpointDAG()
        self.rollback   = RollbackCoordinator()
        self.classifier = ActionClassifier()
        self._agents: dict[str, str] = {}   # agent_id → status

    # ── agent registration ────────────────────────────────────────────────

    def register_agent(self, agent_id: str) -> None:
        self._agents[agent_id] = "idle"
        print(f"[CognitionOS] Agent registered: {agent_id}")

    def agent_status(self, agent_id: str) -> str:
        return self._agents.get(agent_id, "unknown")

    # ── task execution ────────────────────────────────────────────────────

    def run(self, task: str, agent_id: str = "default", files: list[str] | None = None) -> dict[str, Any]:
        """
        End-to-end execution loop:
        1. Schedule task
        2. Retrieve relevant memory & beliefs
        3. Govern context window
        4. Classify risk
        5. Create checkpoint
        6. Execute (simulated) or trigger rollback
        """
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        self._agents[agent_id] = "running"
        start_ts = time.time()

        # 1. Enqueue and dequeue (single-task demo)
        self.scheduler.enqueue(task)
        item = self.scheduler.dequeue()

        # 2. Memory retrieval
        mem_ctx = self.memory.get_context(task)
        self.memory.episodic.record(f"start:{task[:60]}", "scheduled")

        # 3. Retrieve beliefs from Qdrant
        matching_beliefs = self.beliefs.search_beliefs(task, limit=3)

        # 4. Build context items for governance
        context_items = [
            {"content": task, "priority": 1.0, "tag": "current_task"},
            *[{"content": b["belief"], "priority": b.get("confidence", 0.8), "tag": "belief"} for b in matching_beliefs],
            *[{"content": e["step"], "priority": 0.4, "tag": "history"} for e in mem_ctx["recent_history"]],
        ]
        governed = self.governor.govern(context_items)

        # 5. Risk classification
        risk_result = classify_shell(task)
        risk = risk_result["risk"]
        findings = risk_result.get("findings", [])

        # 6. Create semantic checkpoint
        state = AgentState(
            current_goal=task,
            current_plan=f"Execute: {task}",
            active_files=files or ["main.py"],
        )
        checkpoint = self.dag.create_checkpoint(state)
        state_hash = semantic_state_hash(state)

        # 7. Contradiction check against beliefs
        contradictions = []
        for b in matching_beliefs:
            if b.get("score", 0) > 0.85:
                contradictions.append(b["belief"])

        # 8. Decide: allow or rollback
        action_outcome = "executed" if (risk == "LOW" and not contradictions) else "blocked"
        should_rollback = bool(contradictions) or (risk == "HIGH" and findings)

        if should_rollback:
            # Trigger rollback to checkpoint
            restored_state = self.dag.restore_checkpoint(checkpoint.checkpoint_id)
            self.memory.episodic.record(f"rollback:{task[:40]}", "rolled_back", {"reason": "contradiction_or_risk"})
            action_outcome = "rolled_back"
        else:
            self.memory.episodic.record(f"complete:{task[:40]}", "success")

        self._agents[agent_id] = "idle"
        elapsed_ms = (time.time() - start_ts) * 1000

        return {
            "run_id":            run_id,
            "agent_id":          agent_id,
            "task":              task,
            "risk":              risk,
            "findings":          findings,
            "checkpoint_id":     checkpoint.checkpoint_id,
            "state_hash":        state_hash,
            "action_outcome":    action_outcome,
            "contradictions":    contradictions,
            "matching_beliefs":  len(matching_beliefs),
            "context_tokens":    governed["total_tokens"],
            "context_stable":    governed["stable"],
            "elapsed_ms":        round(elapsed_ms, 2),
            "rollback_triggered": should_rollback,
        }
