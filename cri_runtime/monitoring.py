from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .state import AgentState, build_state, semantic_state_hash


@dataclass(frozen=True)
class MonitoringSnapshot:
    task: str
    semantic_state_hash: str
    active_files: list[str]
    telemetry_wal_exists: bool
    telemetry_wal_size_bytes: int
    dashboard_path: str
    datasource_path: str


def collect_snapshot(
    task: str,
    active_files: list[str],
    telemetry_wal_path: str = "/var/log/cri/telemetry_crash.log",
    dashboard_path: str = "grafana/dashboards/cri-runtime-dashboard.json",
    datasource_path: str = "grafana/provisioning/datasources/datasource.yml",
) -> MonitoringSnapshot:
    state: AgentState = build_state(task, active_files)
    wal = Path(telemetry_wal_path)
    return MonitoringSnapshot(
        task=task,
        semantic_state_hash=semantic_state_hash(state),
        active_files=sorted(active_files),
        telemetry_wal_exists=wal.exists(),
        telemetry_wal_size_bytes=wal.stat().st_size if wal.exists() else 0,
        dashboard_path=dashboard_path,
        datasource_path=datasource_path,
    )


def snapshot_to_dict(snapshot: MonitoringSnapshot) -> dict[str, Any]:
    return {
        "task": snapshot.task,
        "semantic_state_hash": snapshot.semantic_state_hash,
        "active_files": snapshot.active_files,
        "telemetry_wal_exists": snapshot.telemetry_wal_exists,
        "telemetry_wal_size_bytes": snapshot.telemetry_wal_size_bytes,
        "dashboard_path": snapshot.dashboard_path,
        "datasource_path": snapshot.datasource_path,
    }
