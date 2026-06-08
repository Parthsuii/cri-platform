from __future__ import annotations

import json
import urllib.request
from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
from packages.contracts.action import CRIAction
from packages.adapters.adapter import GenericAdapter
from packages.events.event import EventFactory
from packages.shared.service_utils import setup_service

app, logger, metrics = setup_service("runtime_kernel")

adapter = GenericAdapter()
event_factory = EventFactory()

def http_post(url: str, data: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"HTTP call to {url} failed: {exc}") from exc

@app.post("/actions")
def handle_action(raw_action: dict = Body(...)) -> dict:
    logger.info("Received raw agent action request", {"payload": raw_action})
    
    # 1. Normalize action using Adapter SDK
    cri_action = adapter.normalize(raw_action)
    logger.info(f"Normalized Action ID: {cri_action.action_id}", {"action_id": cri_action.action_id})
    
    # 2. Emit Telemetry ACTION_PROPOSED
    proposed_event = event_factory.create(cri_action.trace_id, "ACTION_PROPOSED", cri_action.model_dump(), agent_id=cri_action.agent_id)
    logger.info(f"Telemetry Emitted: ACTION_PROPOSED for trace {cri_action.trace_id}", {
        "event_id": proposed_event.event_id,
        "event_type": proposed_event.event_type
    })
    
    # 3. Call Interceptor Service
    try:
        interception = http_post("http://127.0.0.1:8002/intercept", cri_action.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
        
    # 4. Emit Telemetry ACTION_EXECUTED or ACTION_FAILED
    exec_res = interception.get("execution_result") or {}
    returncode = exec_res.get("returncode", 0)
    event_type = "ACTION_EXECUTED" if interception.get("allowed") and returncode == 0 else "ACTION_FAILED"
    execution_event = event_factory.create(cri_action.trace_id, event_type, interception, agent_id=cri_action.agent_id)
    logger.info(f"Telemetry Emitted: {event_type} for trace {cri_action.trace_id}", {
        "event_id": execution_event.event_id,
        "event_type": execution_event.event_type
    })
    
    return interception

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
