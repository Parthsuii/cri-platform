from __future__ import annotations

import json
import urllib.request
from typing import Any
from packages.contracts.action import CRIAction
from packages.adapters.adapter import GenericAdapter

class SDKRuntime:
    def __init__(self) -> None:
        self.agent = None
        self.adapter = GenericAdapter()
        
    def attach(self, agent: Any) -> None:
        self.agent = agent
        
    def execute(self, action: dict | CRIAction) -> dict:
        url = "http://127.0.0.1:8001/actions"
        payload = action if isinstance(action, dict) else action.model_dump()
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"CRI Execution failed: {exc}") from exc

runtime = SDKRuntime()
