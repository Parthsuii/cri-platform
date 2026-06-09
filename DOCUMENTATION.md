# Cognition Runtime Infrastructure (CRI) — Complete Platform Documentation

Welcome to the complete developer and administrator documentation for the **Cognition Runtime Infrastructure (CRI)**. 

CRI acts as **"Kubernetes for Cognition"** — a secure, isolated, observable operating layer and control plane designed specifically for executing, governing, and verifying autonomous agent workloads.

---

## Table of Contents
1. [Core Product Vision](#1-core-product-vision)
2. [Platform Features (What It Does)](#2-platform-features-what-it-does)
3. [System Architecture](#3-system-architecture)
4. [Service Installation & Hosting Guide](#4-service-installation--hosting-guide)
5. [Developer Connection & Integration Guide](#5-developer-connection--integration-guide)
6. [Recent Platform Updates (What We Have Done)](#6-recent-platform-updates-what-we-have-done)

---

## 1. Core Product Vision

CRI is **not** an agent framework (like LangGraph, Autogen, or CrewAI). Instead, it is an **Operating Layer** that external agent workloads run on.

Agents are typically black boxes that run terminal commands, write code, or manipulate databases. CRI intercepts these operations *before* they affect the host system, auditing, isolating, and validating them in real-time.

```
[External Agents (LangGraph, CrewAI)]
              │
              ▼
    [ CRI Control Plane ]  ◄── (Applies Governance & Security Rules)
              │
              ▼
[ Isolated Execution Sandbox ]
```

---

## 2. Platform Features (What It Does)

*   **Pre-Execution Risk Auditing**: Scans proposed actions for critical risk levels (e.g. destructive commands like `rm -rf /` or `DROP TABLE`).
*   **Uniform Policy Enforcement**: Centrally enforces system constraints across all tenants and connected agents (e.g. restricting network access or blocking deployment scripts without operator approval).
*   **Dynamic Sandboxing**: Automatically launches execution tasks inside isolated Docker containers (development) or restricted Kubernetes namespaces (production).
*   **Post-Execution Verification**: Automatically runs tests, syntax compilation checks, and lint rules to verify environmental stability after an agent performs an action.
*   **Automated State Rollback**: If verification checks fail, CRI reverts files and database states back to the last clean snapshot.
*   **Unified Telemetry Bus**: Records all telemetry trace lines and action states to a central Kafka event bus, enabling full execution replays.

---

## 3. System Architecture

CRI is structured as a collection of modular, lightweight microservices communicating via HTTP APIs and a Kafka event stream.

```
                  ┌─────────────────────────────────┐
                  │      External Agent Client      │
                  └────────────────┬────────────────┘
                                   │ (POST /actions)
                                   ▼
                  ┌─────────────────────────────────┐
                  │      Runtime Kernel (:8001)     │
                  └────────┬───────────────┬────────┘
                           │               │
            ┌──────────────┴───────┐       └──────────────┐
            ▼                      ▼                      ▼
┌──────────────────────┐ ┌───────────────────┐ ┌──────────────────────┐
│  Interceptor (:8002) │ │ Risk Engine (:8003│ │ Verification (:8005) │
└──────────┬───────────┘ └───────────────────┘ └──────────┬───────────┘
           │                                              │
           ▼                                              ▼
┌──────────────────────┐                       ┌──────────────────────┐
│   Sandbox (:8004)    │                       │   Rollback (:8009)   │
└──────────────────────┘                       └──────────────────────┘
```

### Microservice Directory

*   **Runtime Kernel (`:8001`)**: The orchestrator gateway that handles actions incoming from the agent SDK.
*   **Interceptor (`:8002`)**: Intercepts actions and routes them to executors based on risk level.
*   **Risk Engine (`:8003`)**: Classifies the security risk of proposed commands.
*   **Sandbox Service (`:8004`)**: Manages the lifecycle of ephemeral, resource-restricted Docker containers and Kubernetes pod jobs.
*   **Verification Engine (`:8005`)**: Checks the workspace integrity post-execution.
*   **Policy Engine (`:8006`)**: Evaluates actions against security compliance rule sets.
*   **State Engine (`:8007`)**: Stores semantic checkpoints and diffs using Qdrant vector embedding stores.
*   **Telemetry Service (`:8008`)**: Centralizes logging and event tracing.
*   **Rollback Service (`:8009`)**: Reverts local directories and states to clean states when verification fails.

---

## 4. Service Setup & Hosting Guide

CRI can be hosted locally or deployed to a distributed Kubernetes cloud cluster.

### Option A: Local Sandbox Setup (Docker Compose)
1.  **Configure Environment**:
    Create a `.env` file in your root folder:
    ```env
    # API Gateway Keys (OpenAI or Groq)
    GROQ_API_KEY=your-groq-api-key-here
    
    # Backing Infrastructure Configurations
    KAFKA_BOOTSTRAP_SERVERS=localhost:9092
    POSTGRES_USER=cri_admin
    POSTGRES_PASSWORD=supersecret
    POSTGRES_URL=jdbc:postgresql://localhost:5432/cri_runtime
    ```
2.  **Start Services**:
    ```bash
    docker-compose up -d
    ```
    This launches the backing Kafka stream, Schema Registry, PostgreSQL, Grafana dashboard, Prometheus collector, Qdrant database, and MinIO storage locally.

### Option B: Cloud/Enterprise Setup (Kubernetes)
1.  **Apply Namespace & RBAC configurations**:
    ```bash
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/serviceaccount.yaml
    kubectl apply -f k8s/role.yaml
    ```
2.  **Set Resource Limits & Network Isolation Policies**:
    ```bash
    kubectl apply -f k8s/resourcequota.yaml
    kubectl apply -f k8s/networkpolicy.yaml
    ```
3.  **Apply Deployment Configurations**:
    ```bash
    kubectl apply -f k8s/configmap.yaml
    ```

---

## 5. Developer Connection & Integration Guide

To connect an external agent tool/workflow to CRI, you can either use our lightweight client SDK or make direct JSON HTTP calls to the gateway.

### The Pydantic Contract (`CRIAction`)
Every request dispatched to the platform must conform to this schema:
```python
class CRIAction(BaseModel):
    action_id: str  # Unique execution UUID
    agent_id: str   # ID of the agent requesting execution
    trace_id: str   # Unique correlation ID for trace lineages
    action_type: str  # e.g., 'shell', 'read_file', 'write_file'
    payload: dict    # Arguments, e.g. {"command": "pip install requests"}
    metadata: dict   # Optional extra context
```

### Python SDK Integration Example
Include the `packages/` directory in your agent's source tree and hook execution:
```python
from packages.sdk.runtime import runtime
from packages.contracts.action import CRIAction

def run_agent_command(command: str):
    action = CRIAction(
        action_id="act-100293",
        agent_id="my-agent-v1",
        trace_id="trace-unique-uuid",
        action_type="shell",
        payload={"command": command}
    )
    
    # Dispatch execution to CRI
    response = runtime.execute(action)
    
    if response["allowed"]:
        print("Success output:", response["execution_result"]["stdout"])
    else:
        print("Blocked by policy:", response["reason"])
```

### Framework Integrations

#### LangGraph Tools Integration
```python
from langchain_core.tools import tool
from packages.sdk.runtime import runtime

@tool
def execute_system_command(command: str) -> str:
    """Executes a system shell command securely via CRI."""
    res = runtime.execute({
        "agent_id": "langgraph-agent",
        "action_type": "shell",
        "payload": {"command": command}
    })
    if not res["allowed"]:
        return f"Error: Command blocked by guardrails. Reason: {res['reason']}"
    return res.get("execution_result", {}).get("stdout", "")
```

#### CrewAI Custom Tool Integration
```python
from crewai.tools import BaseTool
from packages.sdk.runtime import runtime

class CRICmdTool(BaseTool):
    name: str = "CRI Command Executor"
    description: str = "Executes command line inputs after risk auditing."

    def _run(self, command: str) -> str:
        res = runtime.execute({
            "agent_id": "crewai-agent",
            "action_type": "shell",
            "payload": {"command": command}
        })
        if not res["allowed"]:
            return f"Action blocked: {res['reason']}"
        return res.get("execution_result", {}).get("stdout", "Success")
```

---

## 6. Recent Platform Updates (What We Have Done)

In this update cycle, we implemented major performance, compatibility, and diagnostic improvements:

1.  **Unified LLM Gateway (`modules/utils/llm.py`)**: 
    Added dynamic support for the **Groq Cloud API** (running the fast, free-tier `llama-3.3-70b-versatile` model in JSON schema mode) alongside OpenAI's `gpt-4o-mini` parser.
2.  **Environment Variable Autoloader**:
    Implemented a manual `.env` reader within [llm.py](file:///c:/Users/PARTH/New%20folder%20(2)/modules/utils/llm.py) that loads variables directly from the project root.
3.  **Strict Generator Prompts & Constraints**:
    Refined and aligned LLM prompt expectations in the intent, architecture, API, UI, database, and auth generator modules to ensure capitalization, pluralization, and string data type structures align seamlessly across pipeline layers.
4.  **Optimized Repair Parsing**:
    Updated [modules/repair/engine.py](file:///c:/Users/PARTH/New%20folder%20(2)/modules/repair/engine.py) to robustly match multiple validator formats and dynamically split table names regardless of whether endpoint paths are in the error message block.
5.  **Service Startup Stabilization**:
    Adjusted subprocess start sleep times and increased socket timeouts inside [test_cri_platform.py](file:///c:/Users/PARTH/New%20folder%20(2)/tests/test_cri_platform.py) to eliminate flaky platform diagnostics connections refused under heavy CPU loads.
