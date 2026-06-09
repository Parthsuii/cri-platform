from __future__ import annotations

from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
from cri.belief_engine.store import BeliefStore
from .nli import NLIContradictionClassifier

app = FastAPI(title="CRI Verification Engine", version="0.1.0")
store = BeliefStore()
classifier = NLIContradictionClassifier()

class VerificationRequest(BaseModel):
    action_type: str
    payload: dict
    history: list[dict] = []
    retries: int = 0

class VerificationDecision(BaseModel):
    status: str  # PASS, FAIL, RETRY, ROLLBACK
    reason: str
    contradiction_score: float
    violations: list[str]

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "verification_engine"}

@app.post("/verify", response_model=VerificationDecision)
def verify(request: VerificationRequest = Body(...)) -> VerificationDecision:
    command = str(request.payload.get("command", ""))
    if not command:
        command = str(request.payload.get("task", ""))
    
    # 1. Retrieve relevant beliefs from Qdrant
    matching_beliefs = store.search_beliefs(command, limit=3)
    
    violations = []
    max_score = 0.0
    
    # 2. Check contradictions against each belief
    for item in matching_beliefs:
        belief_text = item["belief"]
        score = classifier.check_contradiction(command, belief_text)
        if score > max_score:
            max_score = score
        if score >= 0.7:
            violations.append(f"Violated: '{belief_text}' (score: {score:.2f})")
            
    # Determine decision status
    if violations:
        status = "ROLLBACK" if request.retries >= 1 else "RETRY"
        reason = f"Contradiction detected: {'; '.join(violations)}"
    else:
        status = "PASS"
        reason = "No contradictions detected against system beliefs."

    return VerificationDecision(
        status=status,
        reason=reason,
        contradiction_score=max_score,
        violations=violations
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
