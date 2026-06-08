from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, TypedDict


class AgentState(TypedDict):
    messages: list[Any]
    current_goal: str
    active_files: list[str]
    execution_history: list[dict[str, Any]]
    retries: int


def normalize_history(execution_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entry in execution_history:
        cleaned = {key: value for key, value in entry.items() if key not in {"timestamp", "latency_ms"}}
        normalized.append(cleaned)
    return normalized


def hash_active_files(active_files: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for file_path in sorted(active_files):
        path = Path(file_path)
        if path.exists() and path.is_file():
            result[file_path] = hashlib.md5(path.read_bytes()).hexdigest()
        else:
            result[file_path] = hashlib.md5(b"").hexdigest()
    return result


def semantic_state_hash(state: AgentState) -> str:
    payload = {
        "goal": state["current_goal"],
        "memory": normalize_history(state["execution_history"]),
        "workspace": hash_active_files(state["active_files"]),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_state(current_goal: str, active_files: list[str]) -> AgentState:
    return {
        "messages": [current_goal],
        "current_goal": current_goal,
        "active_files": active_files,
        "execution_history": [],
        "retries": 0,
    }
