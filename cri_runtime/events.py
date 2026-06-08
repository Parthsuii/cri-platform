from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable


REQUIRED_EVENT_KEYS = {"event_type", "timestamp", "payload"}


@dataclass(frozen=True)
class RuntimeEvent:
    event_type: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


class EventValidationError(ValueError):
    pass


class EventFactory:
    def create(self, event_type: str, payload: dict[str, Any]) -> RuntimeEvent:
        return RuntimeEvent(event_type=event_type, payload=payload)


def validate_event(event: dict[str, Any]) -> None:
    missing = REQUIRED_EVENT_KEYS - set(event.keys())
    if missing:
        raise EventValidationError(f"missing event keys: {sorted(missing)}")
    if not isinstance(event["event_type"], str) or not event["event_type"].strip():
        raise EventValidationError("event_type must be a non-empty string")
    if not isinstance(event["payload"], dict):
        raise EventValidationError("payload must be a dictionary")
    if not isinstance(event["timestamp"], (int, float)):
        raise EventValidationError("timestamp must be numeric")


def serialize_event(event: RuntimeEvent) -> str:
    return event.to_json()


def deserialize_event(line: str) -> RuntimeEvent:
    data = json.loads(line)
    validate_event(data)
    return RuntimeEvent(
        event_type=data["event_type"],
        payload=data["payload"],
        timestamp=float(data["timestamp"]),
    )


class EventReplayEngine:
    def load_from_wal(self, wal_path: str) -> list[RuntimeEvent]:
        path = Path(wal_path)
        if not path.exists():
            return []

        events: list[RuntimeEvent] = []
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            events.append(deserialize_event(stripped))
        return events

    def replay(self, wal_path: str) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.load_from_wal(wal_path)]


class TraceManager:
    def __init__(self, trace_path: str = ".sixth/traces/runtime_trace.jsonl") -> None:
        self.trace_path = Path(trace_path)

    def append(self, event: RuntimeEvent) -> None:
        payload = event.to_dict()
        validate_event(payload)
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(serialize_event(event) + "\n")

    def replay(self) -> list[dict[str, Any]]:
        return EventReplayEngine().replay(str(self.trace_path))
