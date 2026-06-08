from __future__ import annotations

from fastapi import FastAPI, Body
from pydantic import BaseModel
from packages.utils.service_utils import setup_service

app, logger, metrics = setup_service("policy_engine")

class PolicyDecision(BaseModel):
    allowed: bool
    action: str  # ALLOW, DENY, SANDBOX, APPROVAL_REQUIRED
    reason: str

@app.post("/evaluate", response_model=PolicyDecision)
def evaluate(payload: dict = Body(...)) -> PolicyDecision:
    action_type = str(payload.get("action_type", ""))
    classification = dict(payload.get("classification", {}))
    risk = str(classification.get("risk", "LOW"))
    route = str(classification.get("route", "direct"))
    command = str(payload.get("command", ""))
    
    logger.info("Evaluating action policy", {"action_type": action_type, "risk": risk})
    
    cmd_lower = command.lower()
    if "deployment" in cmd_lower or "deployment" in action_type.lower() or "deployment" in str(classification.get("reason", "")).lower():
        return PolicyDecision(
            allowed=False,
            action="APPROVAL_REQUIRED",
            reason="Action requires manual operator approval before execution"
        )
    
    if route == "blocked" or risk == "CRITICAL":
        return PolicyDecision(
            allowed=False,
            action="DENY",
            reason="Blocked by critical security risk policy constraint"
        )
        
    if risk == "HIGH":
        return PolicyDecision(
            allowed=True,
            action="SANDBOX",
            reason="Sandbox routing required for execution compliance"
        )
        
    return PolicyDecision(
        allowed=True,
        action="ALLOW",
        reason="Action allowed by standard execution policy"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
