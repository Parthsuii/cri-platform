from __future__ import annotations

import queue
from dataclasses import dataclass
from typing import Any

from .events import RuntimeEvent, validate_event


@dataclass(frozen=True)
class TopicDefinition:
    name: str
    partitions: int = 1
    replication_factor: int = 1


DEFAULT_TOPICS = [
    TopicDefinition("cri.runtime.events"),
    TopicDefinition("cri.runtime.checkpoints"),
    TopicDefinition("cri.runtime.verifications"),
]


class InMemoryKafkaProducer:
    def __init__(self) -> None:
        self.messages: dict[str, list[dict[str, Any]]] = {}

    def publish(self, topic: str, event: RuntimeEvent) -> None:
        payload = event.to_dict()
        validate_event(payload)
        self.messages.setdefault(topic, []).append(payload)


class InMemoryKafkaConsumer:
    def __init__(self, producer: InMemoryKafkaProducer, topic: str) -> None:
        self.topic = topic
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        for message in producer.messages.get(topic, []):
            self._queue.put(message)

    def poll(self, limit: int = 10) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        while len(messages) < limit and not self._queue.empty():
            messages.append(self._queue.get_nowait())
        return messages
