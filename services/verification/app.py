from __future__ import annotations

from fastapi import FastAPI, Body
from pydantic import BaseModel
from packages.utils.service_utils import setup_service

app, logger, metrics = setup_service("verification_engine")

class VerificationDecision(BaseModel):
    status: str  # PASS, FAIL, RETRY, ROLLBACK
    reason: str

@app.post("/verify", response_model=VerificationDecision)
def verify(payload: dict = Body(...)) -> VerificationDecision:
    logger.info("Executing history verification checks")
    history = list(payload.get("history", []))
    retries = int(payload.get("retries", 0))
    
    # Loop history to check failures
    for record in history:
        status = record.get("status")
        output = record.get("output", {})
        
        # Check if record failed or returned non-zero code
        if status != "ok":
            if retries >= 2:
                return VerificationDecision(
                    status="ROLLBACK",
                    reason=f"Step '{record.get('step')}' failed and retry limit exceeded. Initiating rollback."
                )
            return VerificationDecision(
                status="RETRY",
                reason=f"Step '{record.get('step')}' failed. Requesting retry attempt."
            )
            
        result = output.get("result", {})
        if isinstance(result, dict) and result.get("returncode", 0) != 0:
            if retries >= 2:
                return VerificationDecision(
                    status="ROLLBACK",
                    reason=f"Step '{record.get('step')}' returned exit code {result.get('returncode')}. Retry limit reached."
                )
            return VerificationDecision(
                status="RETRY",
                reason=f"Step '{record.get('step')}' returned exit code {result.get('returncode')}."
            )

    return VerificationDecision(
        status="PASS",
        reason="All execution actions verified successfully"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
