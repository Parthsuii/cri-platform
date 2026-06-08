"""Kafka topic definitions for the CRI event backbone."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicSpec:
    name: str
    partitions: int = 3
    replication_factor: int = 1
    retention_ms: int = 604_800_000


CRI_TOPICS: tuple[TopicSpec, ...] = (
    TopicSpec("runtime-events"),
    TopicSpec("telemetry-events"),
    TopicSpec("rollback-events"),
    TopicSpec("verification-events"),
    TopicSpec("policy-events"),
    TopicSpec("runtime-events-dlq"),
)


def kafka_create_topic_commands(bootstrap_server: str = "localhost:9092") -> list[str]:
    return [
        "kafka-topics --create --if-not-exists "
        f"--bootstrap-server {bootstrap_server} "
        f"--topic {topic.name} "
        f"--partitions {topic.partitions} "
        f"--replication-factor {topic.replication_factor} "
        f"--config retention.ms={topic.retention_ms}"
        for topic in CRI_TOPICS
    ]

