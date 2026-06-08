from __future__ import annotations

import json
import urllib.request
from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
from packages.contracts.action import CRIAction
from packages.utils.service_utils import setup_service

app, logger, metrics = setup_service("interceptor")

class InterceptionResult(BaseModel):
    action_id: str
    allowed: bool
    risk: str
    route: str
    reason: str
    execution_result: dict | None = None

def http_post(url: str, data: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"HTTP call to {url} failed: {exc}") from exc

@app.post("/intercept", response_model=InterceptionResult)
def intercept_action(action: CRIAction) -> InterceptionResult:
    logger.info(f"Intercepted action: {action.action_id} of type '{action.action_type}'", {"action_id": action.action_id})
    
    # 1. Call Risk Engine
    try:
        classification = http_post("http://127.0.0.1:8003/classify", {"command": action.payload.get("command", "")})
    except Exception as exc:
        # Fallback if Risk Engine service is offline
        classification = {"risk": "MEDIUM", "reason": f"Risk engine connection error: {exc}", "route": "sandbox"}
        
    risk = classification.get("risk", "LOW")
    route = classification.get("route", "direct")
    risk_reason = classification.get("reason", "")
    
    # 2. Call Policy Engine
    try:
        policy = http_post("http://127.0.0.1:8006/evaluate", {
            "action_type": action.action_type,
            "classification": classification,
            "command": action.payload.get("command", "")
        })
    except Exception as exc:
        # Fallback if Policy Engine service is offline
        policy = {"allowed": True, "action": "ALLOW", "reason": f"Policy engine connection error: {exc}"}
        
    allowed = policy.get("allowed", True)
    policy_reason = policy.get("reason", "")
    
    if not allowed:
        return InterceptionResult(
            action_id=action.action_id,
            allowed=False,
            risk=risk,
            route="blocked",
            reason=policy_reason
        )

    # 3. Route execution if allowed
    execution_result = None
    if route == "sandbox":
        logger.info(f"Routing action {action.action_id} to Sandbox executor")
        try:
            execution_result = http_post("http://127.0.0.1:8004/execute", {"command": action.payload.get("command", "")})
        except Exception as exc:
            execution_result = {"stdout": "", "stderr": f"Sandbox execution failed: {exc}", "returncode": -1}
    else:
        # Direct execution simulation
        logger.info(f"Routing action {action.action_id} to Direct local executor")
        import subprocess
        try:
            res = subprocess.run(
                action.payload.get("command", ""),
                shell=True, capture_output=True, text=True, timeout=10
            )
            execution_result = {"stdout": res.stdout, "stderr": res.stderr, "returncode": res.returncode}
        except Exception as exc:
            execution_result = {"stdout": "", "stderr": str(exc), "returncode": -1}

    return InterceptionResult(
        action_id=action.action_id,
        allowed=True,
        risk=risk,
        route=route,
        reason=f"Risk Engine: {risk_reason}. Policy Engine: {policy_reason}.",
        execution_result=execution_result
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
