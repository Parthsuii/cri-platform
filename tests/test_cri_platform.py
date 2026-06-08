from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
import pytest

def http_post(url: str, data: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))

def http_get(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))

@pytest.fixture(scope="module", autouse=True)
def run_cri_platform():
    # Spin up the services
    services = [
        ("services.risk-engine.app", 8003),
        ("services.policy.app", 8006),
        ("services.sandbox.app", 8004),
        ("services.state-engine.app", 8007),
        ("services.verification.app", 8005),
        ("services.interceptor.app", 8002),
        ("services.runtime-kernel.app", 8001),
        ("services.telemetry.app", 8008),
        ("services.rollback.app", 8009)
    ]
    processes = []
    try:
        for app_module, port in services:
            log_file = open(f"tests/{port}.log", "w", encoding="utf-8")
            proc = subprocess.Popen(
                [sys.executable, "-m", app_module],
                stdout=log_file,
                stderr=log_file
            )
            processes.append((proc, log_file))
        
        # Wait for services to be healthy
        time.sleep(3.5)
        yield
    finally:
        for proc, log_file in processes:
            proc.terminate()
            proc.wait()
            log_file.close()

def test_services_diagnostics_health() -> None:
    # Verify health endpoint on all ports
    for port in [8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009]:
        res = http_get(f"http://127.0.0.1:{port}/health")
        assert res["status"] == "ok"

def test_telemetry_service_records_events() -> None:
    event_payload = {
        "trace_id": "test-trace-123",
        "agent_id": "test-agent-123",
        "event_type": "ACTION_PROPOSED",
        "payload": {"info": "test"}
    }
    res = http_post("http://127.0.0.1:8008/events", event_payload)
    assert res["status"] == "ok"
    assert "event_id" in res
    
    events = http_get("http://127.0.0.1:8008/events")
    assert len(events) > 0
    assert events[-1]["trace_id"] == "test-trace-123"

def test_rollback_service_checkpoint_restore() -> None:
    checkpoint_payload = {
        "reason": "testing rollback service",
        "state": {"step": 1, "status": "checkpointed"}
    }
    checkpoint = http_post("http://127.0.0.1:8009/checkpoints", checkpoint_payload)
    assert "checkpoint_id" in checkpoint
    
    restore_res = http_post(f"http://127.0.0.1:8009/checkpoints/{checkpoint['checkpoint_id']}/restore", {})
    assert restore_res["status"] == "ok"
    assert restore_res["restored_state"]["status"] == "checkpointed"

def test_safe_action_routes_direct() -> None:
    payload = {
        "action_type": "shell",
        "input": {"command": "echo hello_cri"}
    }
    response = http_post("http://127.0.0.1:8001/actions", payload)
    
    assert response["allowed"] is True
    assert response["risk"] == "LOW"
    assert response["route"] == "direct"
    assert "hello_cri" in response["execution_result"]["stdout"]

def test_risky_action_routes_sandbox() -> None:
    payload = {
        "action_type": "shell",
        "input": {"command": "pip install requests"}
    }
    response = http_post("http://127.0.0.1:8001/actions", payload)
    
    assert response["allowed"] is True
    assert response["risk"] == "HIGH"
    assert response["route"] == "sandbox"

def test_forbidden_action_blocked() -> None:
    payload = {
        "action_type": "shell",
        "input": {"command": "rm -rf /"}
    }
    response = http_post("http://127.0.0.1:8001/actions", payload)
    
    assert response["allowed"] is False
    assert response["route"] == "blocked"
    assert "Blocked by critical security risk" in response["reason"]

def test_drop_table_blocked() -> None:
    payload = {
        "action_type": "shell",
        "input": {"command": "DROP TABLE users"}
    }
    response = http_post("http://127.0.0.1:8001/actions", payload)
    
    assert response["allowed"] is False
    assert response["route"] == "blocked"
    assert "Blocked by critical security risk" in response["reason"]

def test_deployment_requires_approval() -> None:
    payload = {
        "action_type": "shell",
        "input": {"command": "deployment setup"}
    }
    response = http_post("http://127.0.0.1:8001/actions", payload)
    
    assert response["allowed"] is False
    assert response["route"] == "blocked"
    assert "Action requires manual operator approval" in response["reason"]
