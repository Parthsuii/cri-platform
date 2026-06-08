from __future__ import annotations

# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from cri_runtime.api import app


client = TestClient(app)


def test_root_endpoint_lists_service_info() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "CRI Runtime Console" in response.text


def test_api_info_endpoint_lists_service_info() -> None:
    response = client.get("/api")

    assert response.status_code == 200
    assert response.json()["name"] == "CRI Runtime Service"
    assert "POST /tasks" in response.json()["endpoints"]


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_submit_and_fetch_agent_task() -> None:
    response = client.post("/tasks", json={"task": "run echo api", "mode": "agent"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["verification"]["passed"] is True

    fetched = client.get(f"/tasks/{payload['task_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["task"] == "run echo api"


def test_rollback_endpoint_restores_checkpoint() -> None:
    created = client.post("/tasks", json={"task": "run echo rollback-api", "mode": "agent"}).json()
    response = client.post("/rollback", json={"checkpoint_id": created["checkpoint_id"]})

    assert response.status_code == 200
    assert response.json()["checkpoint_id"] == created["checkpoint_id"]
    assert response.json()["restored"]["current_goal"] == "run echo rollback-api"


def test_kubernetes_plan_endpoint() -> None:
    response = client.get("/k8s/plan")

    assert response.status_code == 200
    assert response.json()["fabric"] == "kubernetes"
    assert response.json()["apply_order"][0]["path"] == "k8s/namespace.yaml"


def test_compiler_api_endpoints() -> None:
    # Compile
    response = client.post("/compiler/compile", json={"prompt": "Build a CRM with login and contacts"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"]["app_type"] == "crm"
    assert payload["validation"]["valid"] is True

    # History
    history_res = client.get("/compiler/history")
    assert history_res.status_code == 200
    assert len(history_res.json()) == 1
    assert history_res.json()[0]["prompt"] == "Build a CRM with login and contacts"

    # Metrics
    metrics_res = client.get("/compiler/metrics")
    assert metrics_res.status_code == 200
    assert metrics_res.json()["total_compilations"] == 1
    assert metrics_res.json()["success_rate"] == 1.0
