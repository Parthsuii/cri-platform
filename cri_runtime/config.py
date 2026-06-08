"""Configuration primitives for the CRI runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class RuntimeSettings:
    runtime_id: str = "cri-local"
    environment: str = "development"
    kafka_bootstrap_servers: str = "localhost:9092"
    schema_registry_url: str = "http://localhost:8081"
    postgres_dsn: str = "postgresql://cri_admin:supersecret@localhost:5432/cri_runtime"
    qdrant_url: str = "http://localhost:6333"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_bucket: str = "cri-runtime"
    otel_endpoint: str = "http://localhost:4318"
    enabled_plugins: tuple[str, ...] = field(default_factory=tuple)
    default_tenant: str = "default"

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        return cls(
            runtime_id=os.getenv("CRI_RUNTIME_ID", cls.runtime_id),
            environment=os.getenv("CRI_ENVIRONMENT", cls.environment),
            kafka_bootstrap_servers=os.getenv("CRI_KAFKA_BOOTSTRAP_SERVERS", cls.kafka_bootstrap_servers),
            schema_registry_url=os.getenv("CRI_SCHEMA_REGISTRY_URL", cls.schema_registry_url),
            postgres_dsn=os.getenv("CRI_POSTGRES_DSN", cls.postgres_dsn),
            qdrant_url=os.getenv("CRI_QDRANT_URL", cls.qdrant_url),
            object_storage_endpoint=os.getenv("CRI_OBJECT_STORAGE_ENDPOINT", cls.object_storage_endpoint),
            object_storage_bucket=os.getenv("CRI_OBJECT_STORAGE_BUCKET", cls.object_storage_bucket),
            otel_endpoint=os.getenv("CRI_OTEL_ENDPOINT", cls.otel_endpoint),
            enabled_plugins=_csv(os.getenv("CRI_ENABLED_PLUGINS", "")),
            default_tenant=os.getenv("CRI_DEFAULT_TENANT", cls.default_tenant),
        )

