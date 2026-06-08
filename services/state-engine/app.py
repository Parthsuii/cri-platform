from __future__ import annotations

import hashlib
import json
from fastapi import FastAPI, Body
from pydantic import BaseModel
from packages.shared.service_utils import setup_service

app, logger, metrics = setup_service("state_engine")

class HashResult(BaseModel):
    state_hash: str

class SnapshotResult(BaseModel):
    snapshot_id: str
    lineage_parent: str | None

class RuntimeState(BaseModel):
    state_id: str
    parent_state_id: str | None = None
    hash: str

snapshots_db: dict[str, dict] = {}
state_lineage: list[str] = []

@app.post("/hash", response_model=HashResult)
def compute_hash(payload: dict = Body(...)) -> HashResult:
    logger.info("Computing deterministic semantic state hash")
    # Clean/normalize variables to hash deterministically
    normalized = {
        "messages": payload.get("messages", []),
        "current_goal": payload.get("current_goal", ""),
        "active_files": sorted(payload.get("active_files", []))
    }
    dumped = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    state_hash = hashlib.sha256(dumped.encode("utf-8")).hexdigest()
    return HashResult(state_hash=state_hash)

@app.post("/snapshot", response_model=SnapshotResult)
def create_snapshot(payload: dict = Body(...)) -> SnapshotResult:
    state_data = dict(payload.get("state", {}))
    # Compute state hash for unique snapshot ID
    norm_hash = compute_hash(state_data).state_hash
    snapshot_id = f"snap-{norm_hash[:16]}"
    
    parent = state_lineage[-1] if state_lineage else None
    
    snapshots_db[snapshot_id] = {
        "data": state_data,
        "parent": parent,
        "timestamp": payload.get("timestamp")
    }
    state_lineage.append(snapshot_id)
    
    logger.info(f"Created state snapshot: {snapshot_id}", {"snapshot_id": snapshot_id, "parent": parent})
    
    return SnapshotResult(
        snapshot_id=snapshot_id,
        lineage_parent=parent
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
