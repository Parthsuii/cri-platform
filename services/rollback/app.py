from __future__ import annotations

import time
import uuid
from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel, Field
from packages.shared.service_utils import setup_service

app, logger, metrics = setup_service("rollback")

class RollbackCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: f"rollback-{uuid.uuid4().hex[:8]}")
    reason: str
    state: dict
    created_at: float = Field(default_factory=time.time)

# In-memory storage to simulate rollback checkpoints
checkpoints_db: dict[str, RollbackCheckpoint] = {}

@app.post("/checkpoints", response_model=RollbackCheckpoint)
def create_checkpoint(payload: dict = Body(...)) -> RollbackCheckpoint:
    reason = str(payload.get("reason", "Manual checkpoint"))
    state = dict(payload.get("state", {}))
    
    checkpoint = RollbackCheckpoint(reason=reason, state=state)
    checkpoints_db[checkpoint.checkpoint_id] = checkpoint
    
    logger.info(f"Created checkpoint: {checkpoint.checkpoint_id}", {"checkpoint_id": checkpoint.checkpoint_id})
    return checkpoint

@app.post("/checkpoints/{checkpoint_id}/restore")
def restore_checkpoint(checkpoint_id: str) -> dict:
    if checkpoint_id not in checkpoints_db:
        raise HTTPException(status_code=404, detail=f"Checkpoint {checkpoint_id} not found")
        
    checkpoint = checkpoints_db[checkpoint_id]
    logger.info(f"Restored checkpoint: {checkpoint_id}", {"checkpoint_id": checkpoint_id})
    return {
        "status": "ok",
        "checkpoint_id": checkpoint_id,
        "restored_state": checkpoint.state
    }

@app.get("/checkpoints")
def list_checkpoints() -> list[RollbackCheckpoint]:
    return list(checkpoints_db.values())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
