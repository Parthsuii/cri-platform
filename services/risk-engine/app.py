from __future__ import annotations

import yaml
from fastapi import FastAPI, Body
from pydantic import BaseModel
from packages.shared.service_utils import setup_service

app, logger, metrics = setup_service("risk_engine")

class ClassificationResult(BaseModel):
    risk: str
    reason: str
    route: str  # direct, sandbox, blocked

@app.post("/classify", response_model=ClassificationResult)
def classify(payload: dict = Body(...)) -> ClassificationResult:
    command = str(payload.get("command", ""))
    logger.info("Classifying command", {"command": command})
    
    cmd_lower = command.lower()
    
    # Check deny rules
    if "rm -rf" in cmd_lower or "rm " in cmd_lower and "-rf" in cmd_lower:
        return ClassificationResult(
            risk="CRITICAL",
            reason="Forbidden destructive delete command pattern",
            route="blocked"
        )
        
    if "drop table" in cmd_lower:
        return ClassificationResult(
            risk="CRITICAL",
            reason="Forbidden SQL drop table pattern",
            route="blocked"
        )
        
    # Check sandbox rules
    if "deployment" in cmd_lower:
        return ClassificationResult(
            risk="HIGH",
            reason="Sandbox execution required for deployment actions",
            route="sandbox"
        )
        
    if "pip install" in cmd_lower or "npm install" in cmd_lower:
        return ClassificationResult(
            risk="HIGH",
            reason="Sandbox execution required for dependency installation",
            route="sandbox"
        )
        
    if "rm " in cmd_lower or "mv " in cmd_lower or "chmod " in cmd_lower:
        return ClassificationResult(
            risk="MEDIUM",
            reason="Mutation action requiring containment",
            route="sandbox"
        )

    return ClassificationResult(
        risk="LOW",
        reason="Safe command execution",
        route="direct"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
