from __future__ import annotations

import json
import time
import hashlib
from pathlib import Path
from typing import Any

_MEMORY_FILE = Path(".cri_episodic_memory.jsonl")


class EpisodicMemory:
    """
    Stores a sequential, append-only log of agent execution steps.
    Acts as the agent's working memory across runs.
    """
    def __init__(self) -> None:
        self._log: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if _MEMORY_FILE.exists():
            try:
                for line in _MEMORY_FILE.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        self._log.append(json.loads(line))
            except Exception:
                self._log = []

    def record(self, step: str, outcome: str, metadata: dict | None = None) -> str:
        entry_id = hashlib.md5(f"{step}-{time.time()}".encode()).hexdigest()[:12]
        entry = {
            "id": entry_id,
            "step": step,
            "outcome": outcome,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        self._log.append(entry)
        try:
            with _MEMORY_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
        return entry_id

    def recent(self, n: int = 20) -> list[dict[str, Any]]:
        return self._log[-n:]

    def search(self, keyword: str) -> list[dict[str, Any]]:
        kw = keyword.lower()
        return [e for e in self._log if kw in e.get("step", "").lower() or kw in e.get("outcome", "").lower()]


class SemanticMemory:
    """
    Stores and retrieves semantic guidelines and architectural principles.
    Uses simple keyword index for fast retrieval without vector overhead.
    """
    def __init__(self) -> None:
        self._guidelines: list[dict[str, str]] = [
            {"key": "security",     "rule": "All shell commands must pass through the CRI interceptor before execution."},
            {"key": "idempotency",  "rule": "Agent actions must be idempotent — re-running them must not cause side effects."},
            {"key": "traceability", "rule": "Every agent action must emit a telemetry event with a valid trace_id."},
            {"key": "rollback",     "rule": "A semantic checkpoint must be created before any HIGH-risk action is dispatched."},
            {"key": "sandbox",      "rule": "HIGH-risk actions are automatically routed to the sandbox execution pool."},
            {"key": "contradiction","rule": "Actions contradicting extracted codebase beliefs trigger the contradiction router."},
        ]

    def retrieve(self, context: str, top_k: int = 3) -> list[dict[str, str]]:
        ctx = context.lower()
        scored = []
        for g in self._guidelines:
            score = sum(1 for w in g["key"].split() if w in ctx)
            score += sum(1 for w in g["rule"].lower().split() if w in ctx and len(w) > 4)
            scored.append((score, g))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [g for _, g in scored[:top_k] if _ >= 0]

    def all(self) -> list[dict[str, str]]:
        return list(self._guidelines)


class MemoryArbitrator:
    """
    Combines episodic + semantic memory to provide relevant context
    for the next agent planning step.
    """
    def __init__(self) -> None:
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()

    def get_context(self, current_task: str, top_k_episodic: int = 5) -> dict[str, Any]:
        recent_steps = self.episodic.recent(top_k_episodic)
        guidelines   = self.semantic.retrieve(current_task)
        return {
            "recent_history":     recent_steps,
            "applicable_rules":   guidelines,
            "task":               current_task,
        }
