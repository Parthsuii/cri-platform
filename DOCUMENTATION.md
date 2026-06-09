# Cognition Reliability Infrastructure (CRI) — Complete Platform Documentation

Welcome to the complete reference manual for the **Cognition Reliability Infrastructure (CRI)**.

CRI acts as **"Kubernetes for Cognition"** — a secure, isolated, observable operating layer and control plane designed specifically to run, govern, and verify autonomous AI agent workloads.

---

## 1. What Our Product Does

CRI is **not** an agent framework (like LangGraph, AutoGen, or CrewAI). Instead, it is an **Operating Layer** that wraps external agent workloads, intercepting their actions *before* they affect the host environment.

```
┌───────────────────────────────────────────────┐
│     External Agents (LangGraph, CrewAI)       │
└───────────────────────┬───────────────────────┘
                        │
                        ▼ (Sends Actions)
┌───────────────────────────────────────────────┐
│              CRI Control Plane                │  ◄── Enforces Security Guards
└───────────────────────┬───────────────────────┘
                        │
                        ▼ (Isolated Runs)
┌───────────────────────────────────────────────┐
│         Isolated Execution Sandbox            │
└───────────────────────────────────────────────┘
```

### Core Features
*   **Action Interception**: Captures shell, file, and database operations before execution.
*   **Real-time Risk Classification**: Automatically assigns risk categories (SAFE, LOW, MEDIUM, HIGH, CRITICAL).
*   **Unified Policy Guardrails**: Enforces compliance checks across multiple agents and tenants.
*   **Isolated Ephemeral Sandboxing**: Executes shell commands inside Docker containers or isolated Kubernetes pods.
*   **Post-Execution Verification**: Tests system state integrity immediately after execution.
*   **Automated State Rollback**: Automatically reverts filesystem and database modifications to the last clean checkpoint if verification checks fail.
*   **Unified Event Telemetry**: Emits telemetry trace events to a central Apache Kafka event bus.

---

## 2. How Our Product Protects Your Product

CRI keeps production hosts, software repositories, and backend databases safe from agent errors by employing a multi-layered defense strategy:

```
Proposed Action
      │
      ▼
┌───────────┐      Critical risk / policy violation?
│Risk Engine│ ──► [YES] ──► Block action immediately.
└─────┬─────┘
      │ [NO]
      ▼
┌───────────┐
│  Sandbox  │ ──► Executes code in isolated containers.
└─────┬─────┘
      │
      ▼
┌───────────┐      State damaged / test failed?
│Verify/Test│ ──► [YES] ──► Revert changes (Rollback).
└─────┬─────┘
      │ [NO]
      ▼
 Apply to Host
```

*   **Risk Auditing**: Intercepts command inputs, identifying dangerous strings (e.g. `rm -rf /` or `DROP TABLE`) and blocks them.
*   **Isolate & Contain**: Commands run inside restricted sandboxes with limits on CPU, RAM, and network connections.
*   **Verification Gateways**: Instantly checks files, compilation syntax, and test statuses after each action.
*   **Fail-Safe Rollbacks**: Reverts the environment back to a clean state if any test fails, preventing broken or corrupted deployments.

---

## 3. Step-by-Step Setup & Hosting

CRI supports local Docker containers for development and distributed Kubernetes clusters for production.

### Step A: Configure API Keys & Fallback Options
Create a [`.env`] file in the root workspace folder:

```env
# Agent Runtime Provider Keys
OPENROUTER_API_KEY=sk-or-v1-your-key-here
GROQ_API_KEY=gsk_your-groq-api-key-here
OPENAI_API_KEY=sk-...

# Infrastructure Configurations
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
POSTGRES_USER=cri_admin
POSTGRES_PASSWORD=supersecret
POSTGRES_URL=jdbc:postgresql://localhost:5432/cri_runtime
```

> [!NOTE]
> **LLM Priority Failover**: The runtime attempts to use OpenRouter first (configured for the free Llama-3.3-70B model). If OpenRouter hits rate limits, it automatically falls back to Groq, and then to OpenAI.

### Step B: Start Local Services (Docker Compose)
Start the core backing infrastructure services locally:
```bash
docker-compose up -d
```
This starts:
*   **Kafka** (`localhost:9092`)
*   **Postgres** (`localhost:5432`)
*   **Prometheus** (`localhost:9090`)
*   **Grafana** (`localhost:3000`)
*   **Qdrant Vector DB** (`localhost:6333`)
*   **MinIO Storage** (`localhost:9000`)

### Step C: Apply Production Kubernetes Configurations
For containerized Kubernetes production deployment, run:
```bash
# Setup namespaces and access permissions
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/role.yaml

# Set quotas and network security policies
kubectl apply -f k8s/resourcequota.yaml
kubectl apply -f k8s/networkpolicy.yaml

# Deploy config maps and microservices
kubectl apply -f k8s/configmap.yaml
```

---

## 4. How to Use CRI

You can interact with CRI using our SDK, HTTP API endpoints, framework tool wrappers, or the Console UI.

### Option A: Using the Python SDK
Copy the `packages/` directory into your project root and instantiate the client runtime:

```python
from packages.sdk.runtime import runtime
from packages.contracts.action import CRIAction

# 1. Define the action to audit
action = CRIAction(
    action_id="act-100293",
    agent_id="my-agent-v1",
    trace_id="trace-unique-uuid",
    action_type="shell",
    payload={"command": "pip install requests"}
)

# 2. Dispatch the action
response = runtime.execute(action)

# 3. Process the response
if response["allowed"]:
    print("Execution Success:", response["execution_result"]["stdout"])
else:
    print("Action Blocked:", response["reason"])
```

### Option B: Framework Integrations
Easily wrap execution functions inside agent frameworks:

#### 1. LangGraph Tool Wrapper
```python
from langchain_core.tools import tool
from packages.sdk.runtime import runtime

@tool
def secure_shell(command: str) -> str:
    """Executes a system shell command securely via CRI."""
    res = runtime.execute({
        "agent_id": "langgraph-agent",
        "action_type": "shell",
        "payload": {"command": command}
    })
    if not res["allowed"]:
        return f"Action blocked: {res['reason']}"
    return res.get("execution_result", {}).get("stdout", "")
```

#### 2. CrewAI Tool Wrapper
```python
from crewai.tools import BaseTool
from packages.sdk.runtime import runtime

class CRICmdTool(BaseTool):
    name: str = "CRI Tool"
    description: str = "Executes command line inputs after risk auditing."

    def _run(self, command: str) -> str:
        res = runtime.execute({
            "agent_id": "crewai-agent",
            "action_type": "shell",
            "payload": {"command": command}
        })
        return res.get("execution_result", {}).get("stdout", f"Blocked: {res.get('reason')}")
```

### Option C: Running the Console Web UI
Start the CRI Runtime Console:
```bash
python main.py --serve --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser. This web console allows you to submit tasks, track telemetry traces, inspect Kubernetes plans, and execute prompt compilations.

---

## 5. Target Use Cases

*   **Secure Code Sandbox**: Safely run untrusted user code or LLM-generated scripts.
*   **Database Guardrails**: Intercept SQL queries or schema alterations to prevent SQL injection or deletion.
*   **Multi-Agent Environments**: Manage, trace, and audit actions across a swarm of autonomous agents.
*   **Agent Deployment Verification**: Automatically verify code compilations and run unit tests before allowing agents to commit or deploy software.

---

## 6. How Our System Works in Detail

CRI uses a distributed microservice design. The kernel acts as the routing gateway, calling other components depending on the step of the lifecycle:

```
                       [ External Agent ]
                               │
                               ▼ (POST /actions)
┌─────────────────────────────────────────────────────────────────────────┐
│                         CRI Runtime Kernel                              │
└──────┬──────────────────────┬──────────────────────┬─────────────┬──────┘
       │                      │                      │             │
       ▼                      ▼                      ▼             ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐ ┌──────────┐
│ Interceptor  │ ◄───► │ Risk Engine  │ ◄───► │ Verification │ │ Telemetry│
└──────┬───────┘       └──────────────┘       └──────┬───────┘ └──────────┘
       │                                             │
       ▼                                             ▼
┌──────────────┐                              ┌──────────────┐
│ Sandbox Pool │                              │   Rollback   │
└──────────────┘                              └──────────────┘
```

### Microservice Components
1.  **Runtime Kernel (`:8001`)**: The ingress port that receives, deserializes, and guides proposed actions.
2.  **Interceptor (`:8002`)**: Determines how to route execution (e.g. local process for safe actions, isolated container for riskier commands, or blocked).
3.  **Risk Engine (`:8003`)**: Runs heuristic parsers and lightweight zero-shot classification models to flag dangerous actions.
4.  **Sandbox Pool (`:8004`)**: Dynamically boots, manages, and executes commands inside resource-capped containers.
5.  **Verification Engine (`:8005`)**: Monitors environmental metrics, linting status, and test outputs post-execution.
6.  **Policy Engine (`:8006`)**: Evaluates policies to confirm if actions fit resource limits and access constraints.
7.  **State Engine (`:8007`)**: Builds semantic files state hashes using vector embedding engines.
8.  **Telemetry Service (`:8008`)**: Gathers traces and pushes logs to Grafana/Prometheus.
9.  **Rollback Engine (`:8009`)**: Reverts directory changes or restores state checkpoints when verification fails.
