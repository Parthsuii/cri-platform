from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SandboxClaim:
    container_id: str
    claimed_at: float = field(default_factory=time.time)
    workspace: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="cri-sandbox-")))


class SandboxPoolManager:
    def __init__(self, image: str = "cri-sandbox-base", pool_size: int = 3) -> None:
        self.image = image
        self.pool_size = pool_size
        self._idle: list[SandboxClaim] = [SandboxClaim(container_id=f"{image}-{idx}") for idx in range(pool_size)]

    def claim(self) -> SandboxClaim:
        if self._idle:
            return self._idle.pop(0)
        return SandboxClaim(container_id=f"{self.image}-{int(time.time() * 1000)}")

    def release(self, claim: SandboxClaim) -> None:
        if len(self._idle) < self.pool_size:
            self._idle.append(claim)

    def exec_in_sandbox(self, claim: SandboxClaim, command: str) -> dict[str, Any]:
        try:
            claim.workspace.mkdir(parents=True, exist_ok=True)
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=False,
                cwd=claim.workspace,
            )
            return {
                "container_id": claim.container_id,
                "workspace": str(claim.workspace),
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        finally:
            self.release(claim)
