# CRI Runtime — Local Infrastructure

This repository includes a development `docker-compose` that brings up local services used by the CRI runtime for development and testing.

Quick start:

1. Set a Postgres password (optional):

```
export POSTGRES_PASSWORD=supersecret
```

2. Start services:

```
docker-compose up -d
```

3. Services available:
- Kafka: localhost:9092
- Schema Registry: localhost:8081
- Postgres: localhost:5432
- Grafana: localhost:3000 (admin/admin)
- Prometheus: localhost:9090
- OpenTelemetry Collector OTLP: 4317/4318
- Qdrant: localhost:6333
- MinIO: localhost:9000 (minio/minio123)

Notes:
- Prometheus and OpenTelemetry collector are provided with minimal configs for local development.
- Adjust `POSTGRES_PASSWORD` and other secrets for production use.

Infrastructure cross-check:
- See `CRI_Platform_Infrastructure_Gap_Report.md` for the checklist audit and newly added platform pieces.
- Kafka topic specs are in `kafka-topics.json` and `cri_runtime/topics.py`.
- PostgreSQL runtime tables are initialized by `postgres/init/002_runtime_tables.sql`.
- Kubernetes quota, network policy, and RBAC manifests are under `k8s/`.

---

## Connecting External Agents to CRI

Other developers can connect their autonomous agents to the CRI Platform to automatically intercept, validate, sandbox, and track executions.

### 1. Requirements to Connect (What is Required)

To successfully establish a connection to CRI, ensure the following prerequisites are met:
*   **Active Microservices:** The CRI platform services must be running. You can launch them locally in development mode by starting the services:
    *   Runtime Kernel (`services.runtime-kernel.app`) on Port `8001`
    *   Interceptor (`services.interceptor.app`) on Port `8002`
    *   Risk Engine (`services.risk-engine.app`) on Port `8003`
    *   Sandbox (`services.sandbox.app`) on Port `8004`
    *   Verification (`services.verification.app`) on Port `8005`
    *   Policy (`services.policy.app`) on Port `8006`
    *   State Engine (`services.state-engine.app`) on Port `8007`
*   **Local Python Packages:** Ensure the `packages/` namespace is in the agent's Python search path (or copy `packages/sdk`, `packages/contracts`, `packages/adapters`, and `packages/shared` directly into the agent's repository).
*   **JSON Schema Prerequisites:** Your agent must supply the following fields in every request payload:
    *   `agent_id`: A unique string identifier representing the agent (e.g., `langgraph-agent-12`).
    *   `trace_id`: A correlation ID representing the lifecycle/run lineage (e.g., `trace-928ab1`).
    *   `action_type`: The category of the operation (e.g., `shell`, `read_file`, `write_file`).
    *   `payload`: A dictionary containing the actual execution command arguments (e.g., `{"command": "pip install requests"}`).
    *   `metadata`: (Optional) Custom dictionary context.

---

### 2. How to Connect (Step-by-Step)

#### Step A: Expose the API Port
Start the microservice stack. By default, the Runtime Kernel binds to `127.0.0.1:8001`. Ensure your network config allows the agent's runtime environment to reach `http://127.0.0.1:8001`.

#### Step B: Integrate the SDK or Client
Copy the `packages/` directory into your project root. You can import the SDK runtime module:
```python
from packages.sdk import runtime
```

---

### 3. How to Use (Integration Examples)

#### Option A: Using the Python SDK

Developers can attach their agent instances and call `runtime.execute` inside their tool execution hooks. This intercepts commands before executing them in production:

```python
from packages.sdk import runtime

# 1. Attach your agent workload to instrument it
runtime.attach(my_agent)

# 2. Dispatch a proposed action payload to the CRI kernel
result = runtime.execute({
    "agent_id": "langgraph-agent-1",
    "action_type": "shell",
    "payload": {
        "command": "pip install requests"
    }
})

# 3. Handle the CRI policy/risk engine response
if result["allowed"]:
    print(f"Action allowed! Route chosen: {result['route']}")
    print(f"Result Output: {result.get('execution_result', {}).get('stdout')}")
else:
    print(f"Action blocked by policy! Reason: {result['reason']}")
```

#### Option B: Direct HTTP Connection (Cross-Language)

For agents written in Go, JavaScript/TypeScript, or other runtimes, use direct JSON POST requests to communicate with the kernel API:

```bash
curl -X POST http://127.0.0.1:8001/actions \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "external-javascript-agent",
    "action_type": "shell",
    "payload": {
      "command": "DROP TABLE users"
    }
  }'
```

**Expected Response (Blocked Example):**
```json
{
  "action_id": "act-bc128a3f89ca",
  "allowed": false,
  "risk": "CRITICAL",
  "route": "blocked",
  "reason": "Risk Engine: Forbidden SQL drop table pattern. Policy Engine: Blocked by critical security risk policy constraint."
}
```
