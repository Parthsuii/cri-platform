from __future__ import annotations

from fastapi import FastAPI, Body
from packages.events.event import CRIEvent
from packages.shared.service_utils import setup_service

app, logger, metrics = setup_service("telemetry")

# In-memory storage to simulate telemetry event logging
events_db: list[CRIEvent] = []

@app.post("/events")
def record_event(event: CRIEvent = Body(...)) -> dict:
    logger.info(f"Recorded event: {event.event_type} (Trace ID: {event.trace_id})", {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "trace_id": event.trace_id,
        "agent_id": event.agent_id
    })
    events_db.append(event)
    return {"status": "ok", "event_id": event.event_id}

@app.get("/events")
def list_events() -> list[CRIEvent]:
    return events_db

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
