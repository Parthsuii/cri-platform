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

Other developers can connect their autonomous agents to the CRI Platform using either the Python SDK or the REST API.

### Option 1: Using the Python SDK

Import the runtime client, attach your agent, and dispatch actions through the CRI gateway to automatically leverage the policy, risk classification, and sandboxing infrastructure:

```python
from packages.sdk import runtime

# 1. Attach your agent workload to instrument it
runtime.attach(my_agent)

# 2. Dispatch the proposed action through the CRI control plane
result = runtime.execute({
    "agent_id": "langgraph-agent-1",
    "action_type": "shell",
    "payload": {
        "command": "pip install requests"
    }
})

print(f"Action Allowed: {result['allowed']}")
print(f"Execution Route: {result['route']}")
print(f"Stdout: {result.get('execution_result', {}).get('stdout')}")
```

### Option 2: Using the HTTP REST API

For agents built in other languages (Go, JavaScript/TypeScript, etc.), they can communicate directly with the Runtime Kernel API Gateway:

```bash
curl -X POST http://127.0.0.1:8001/actions \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "external-agent",
    "action_type": "shell",
    "payload": {
      "command": "echo hello_cri"
    }
  }'
```

When an action is submitted via the HTTP API, it will run through the complete normalization, risk engine classification, policy engine evaluation, sandbox routing, telemetry publishing, and verification pipeline automatically.
