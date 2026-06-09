from __future__ import annotations

import json
import urllib.request
from typing import Any
from .action import CRIAction

class RuntimeWrapper:
    def __init__(self, kernel_url: str = "http://127.0.0.1:8001/actions") -> None:
        self.kernel_url = kernel_url
        self.agent = None

    def attach(self, agent: Any) -> None:
        """Attaches the client SDK to instrument an agent workload."""
        self.agent = agent

    def execute(self, action: dict | CRIAction) -> dict:
        """Dispatches a proposed action to the CRI execution kernel."""
        payload = action if isinstance(action, dict) else action.model_dump()
        req = urllib.request.Request(
            self.kernel_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"CRI Kernel connection refused or failed: {exc}") from exc

runtime = RuntimeWrapper()
