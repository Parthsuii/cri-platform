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
