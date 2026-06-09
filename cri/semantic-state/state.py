from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    current_goal: str = Field(default="")
    current_plan: str = Field(default="")
    constraints: list[str] = Field(default_factory=list)
    active_files: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    execution_history: list[dict[str, Any]] = Field(default_factory=list)

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
            try:
                result[file_path] = hashlib.md5(path.read_bytes()).hexdigest()
            except Exception:
                result[file_path] = hashlib.md5(b"").hexdigest()
        else:
            result[file_path] = hashlib.md5(b"").hexdigest()
    return result

def semantic_state_hash(state: AgentState) -> str:
    payload = {
        "goal": state.current_goal,
        "plan": state.current_plan,
        "constraints": sorted(state.constraints),
        "memory": normalize_history(state.execution_history),
        "workspace": hash_active_files(state.active_files),
        "dependencies": sorted(state.dependencies)
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
