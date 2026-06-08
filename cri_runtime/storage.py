"""Storage contracts and DDL for persistent CRI runtime state."""

from __future__ import annotations

from dataclasses import dataclass


RUNTIME_TABLES_DDL = """
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    root_event_id UUID,
    status TEXT NOT NULL DEFAULT 'open',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id UUID PRIMARY KEY,
    trace_id TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    object_key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    policy_type TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    definition JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rollbacks (
    id UUID PRIMARY KEY,
    checkpoint_id UUID NOT NULL,
    trace_id TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    decision TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


@dataclass(frozen=True)
class ObjectKeyBuilder:
    bucket: str = "cri-runtime"

    def snapshot_key(self, trace_id: str, checkpoint_id: str) -> str:
        return f"snapshots/{trace_id}/{checkpoint_id}.json"

    def log_key(self, trace_id: str, event_id: str) -> str:
        return f"logs/{trace_id}/{event_id}.json"

    def artifact_key(self, trace_id: str, artifact_name: str) -> str:
        safe_name = artifact_name.replace("\\", "/").split("/")[-1]
        return f"artifacts/{trace_id}/{safe_name}"

