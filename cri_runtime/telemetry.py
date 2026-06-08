from __future__ import annotations

import json
import os
import queue
import threading
from pathlib import Path
from typing import Any

from .events import EventFactory, RuntimeEvent, serialize_event, validate_event


class TelemetryEmitter:
    def __init__(self, bootstrap_servers: str | None = None, wal_path: str = "/var/log/cri/telemetry_crash.log") -> None:
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.wal_path = Path(wal_path)
        self.queue: queue.Queue[RuntimeEvent] = queue.Queue(maxsize=1024)
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._factory = EventFactory()
        self._worker.start()

    def emit(self, event: dict[str, Any] | RuntimeEvent) -> None:
        if isinstance(event, RuntimeEvent):
            runtime_event = event
        else:
            event_type = event.get("event_type") or event.get("type")
            payload = event.get("payload")
            if payload is None:
                payload = {key: value for key, value in event.items() if key not in {"event_type", "type"}}
            runtime_event = self._factory.create(str(event_type), payload)
        try:
            self.queue.put_nowait(runtime_event)
        except queue.Full:
            self._append_wal(runtime_event)

    def close(self) -> None:
        self._stop.set()
        self._worker.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                event = self.queue.get(timeout=0.25)
            except queue.Empty:
                continue
            if not self._publish(event):
                self._append_wal(event)

    def _publish(self, event: RuntimeEvent) -> bool:
        try:
            payload = event.to_dict()
            validate_event(payload)
            _ = self.bootstrap_servers
            _ = serialize_event(event)
            return True
        except Exception:
            return False

    def _append_wal(self, event: RuntimeEvent) -> None:
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        with self.wal_path.open("a", encoding="utf-8") as handle:
            handle.write(serialize_event(event) + "\n")
