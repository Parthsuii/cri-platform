from __future__ import annotations

import copy
import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RollbackCheckpoint:
    checkpoint_id: str
    reason: str
    state: dict[str, Any]
    created_at: float = field(default_factory=time.time)


class DistributedRollbackManager:
    def __init__(self) -> None:
        self._checkpoints: dict[str, RollbackCheckpoint] = {}
        self._sequence = 0

    def create_checkpoint(self, state: dict[str, Any], reason: str) -> RollbackCheckpoint:
        self._sequence += 1
        checkpoint = RollbackCheckpoint(
            checkpoint_id=f"rollback-{self._sequence}",
            reason=reason,
            state=copy.deepcopy(state),
        )
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        return checkpoint

    def restore(self, checkpoint_id: str) -> dict[str, Any]:
        if checkpoint_id not in self._checkpoints:
            raise KeyError(f"unknown checkpoint: {checkpoint_id}")
        return copy.deepcopy(self._checkpoints[checkpoint_id].state)

    def list_checkpoints(self) -> list[dict[str, Any]]:
        return [asdict(checkpoint) for checkpoint in self._checkpoints.values()]
