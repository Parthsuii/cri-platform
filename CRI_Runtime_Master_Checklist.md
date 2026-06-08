# CRI Platform

# MASTER_BUILD_SPEC_V4.md

## Cognition Runtime Infrastructure

### Infrastructure For Autonomous Systems

Version: 4.0

Status: Authoritative Build Specification

---

# 1. Vision

CRI is the runtime operating layer for autonomous systems.

CRI is not:

* Agent Framework
* Workflow Engine
* LLM Provider
* Chat Platform
* Prompt Framework

CRI provides:

* Action Interception
* Risk Classification
* Sandbox Execution
* Verification
* Rollback
* Telemetry
* Governance
* Observability

---

# 2. Core Philosophy

Current AI Architecture:

```text
LLM
 ↓
Agent
 ↓
Production
```

CRI Architecture:

```text
LLM
 ↓
Agent
 ↓
CRI Runtime
 ↓
Production
```

CRI becomes the control plane between autonomous systems and the real world.

---

# 3. Technology Stack

## Runtime

* Python 3.12
* FastAPI
* Pydantic v2
* SQLAlchemy

## Database

* PostgreSQL

## Event Streaming

* Apache Kafka

## Object Storage

* MinIO

## Vector Database

* Qdrant

## Container Runtime

* Docker

## Orchestration

* Kubernetes (later)

## Telemetry

* OpenTelemetry
* Prometheus
* Grafana

---

# 4. Model Layer (100% Free)

## Reasoning

Qwen 3 8B

Purpose:

* planning
* tool usage
* reasoning

---

## Coding

DeepSeek R1 Distill

Purpose:

* code generation
* code modification

---

## Embeddings

BGE Large

Purpose:

* semantic search
* state similarity
* contradiction detection

---

## Inference

vLLM

Purpose:

Serve all models locally.

No OpenAI.

No Anthropic.

No monthly costs.

---

# 5. Final Architecture

```text
Developer
    │
    ▼

CRI SDK

    │
    ▼

API Gateway

    │
    ▼

Runtime Kernel

    │
    ▼

Adapter Layer

    │
    ▼

Interceptor Engine

    │
    ▼

Risk Engine

    │
    ▼

Execution Router

 ┌───────────────┐
 │               │

 ▼               ▼

Direct       Sandbox

 │               │

 └──────┬────────┘

        ▼

Verification

        ▼

Rollback

        ▼

Telemetry

        ▼

Kafka

        ▼

PostgreSQL

Qdrant

MinIO

        ▼

Dashboard
```

---

# 6. Repository Structure

```text
cri-platform/

apps/

services/

packages/

deployment/

tests/

docs/
```

---

## Services

```text
api-gateway/

runtime-kernel/

adapter-service/

interceptor/

risk-engine/

telemetry/

sandbox/

verification/

rollback/

policy/

state-engine/

model-gateway/

dashboard/
```

---

## Packages

```text
contracts/

events/

adapters/

sdk/

shared/
```

---

# 7. Phase 1

## Runtime Foundation

Timeline:

Week 1–2

Goal:

Receive actions.

---

## Build

### API Gateway

Endpoints:

POST /v1/actions

GET /health

GET /metrics

---

### Runtime Kernel

Responsibilities:

* action orchestration
* routing
* lifecycle

---

### Action Contract

```python
class CRIAction:

    action_id: str

    trace_id: str

    agent_id: str

    action_type: str

    payload: dict

    metadata: dict
```

---

### SDK

```python
runtime.attach(agent)

runtime.execute(action)
```

---

## Checklist

* [x] Runtime Kernel
* [x] SDK
* [x] Action Contract
* [x] API Gateway

Acceptance:

Action successfully received.

---

# 8. Phase 2

## Adapter Layer

Timeline:

Week 2–3

Goal:

Integrate existing agents.

---

### Adapters

Generic

LangGraph

OpenAI Agents

AutoGen

OpenHands

CrewAI

---

### Adapter Interface

```python
class Adapter:

    def normalize(
        self,
        action
    ):
        pass
```

---

## Checklist

* [x] Generic Adapter
* [x] LangGraph Adapter
* [x] OpenAI Adapter

Acceptance:

External agents connected.

---

# 9. Phase 3

## Interceptor Engine

Timeline:

Week 3–5

Goal:

Nothing bypasses CRI.

---

### Flow

```text
Action
 ↓
Interceptor
 ↓
Middleware
 ↓
Risk
 ↓
Router
```

---

### Middleware

Auth

Telemetry

Policy

Risk

---

## Checklist

* [x] Interceptor
* [x] Middleware
* [x] Router

Acceptance:

100% action interception.

---

# 10. Phase 4

## Risk Engine

Timeline:

Week 5–6

Goal:

Classify actions.

---

### Risk Levels

LOW

MEDIUM

HIGH

CRITICAL

---

### Rules

```yaml
deny:

  - rm -rf

  - DROP TABLE

sandbox:

  - pip install

  - deployment
```

---

### Future

Qwen-powered semantic risk analysis.

---

## Checklist

* [x] Rule Engine
* [x] Classifier

Acceptance:

Risk classification operational.

---

# 11. Phase 5

## Telemetry Platform

Timeline:

Week 6–8

Goal:

Everything becomes telemetry.

---

### Event Types

ACTION_PROPOSED

ACTION_EXECUTED

ACTION_FAILED

CHECKPOINT_CREATED

ROLLBACK_TRIGGERED

POLICY_VIOLATION

STATE_UPDATED

---

### Event Store

PostgreSQL

Tables:

events

actions

traces

---

## Checklist

* [x] Event Factory
* [x] Event Store
* [x] Trace Engine

Acceptance:

Replay possible.

---

# 12. Phase 6

## Dashboard

Timeline:

Week 8–9

Goal:

Developer visibility.

---

### Pages

Runtime Explorer

Trace Explorer

Risk Explorer

Rollback Explorer

---

## Frontend

Next.js

Tailwind

shadcn/ui

---

## Checklist

* [x] Runtime View
* [x] Trace View

Acceptance:

Action history visible.

---

# 13. Phase 7

## Sandbox Platform

Timeline:

Week 9–11

Goal:

Safe execution.

---

### Runtime

Docker

---

### Controls

CPU

Memory

Filesystem

Network

---

### Router

LOW

Direct

HIGH

Sandbox

---

## Checklist

* [x] Sandbox Runtime
* [x] Docker Executor

Acceptance:

High-risk actions isolated.

---

# 14. Phase 8

## Verification Platform

Timeline:

Week 11–12

Goal:

Validate outcomes.

---

### Checks

Build

Tests

Dependencies

Artifacts

---

### Results

PASS

FAIL

RETRY

ROLLBACK

---

## Checklist

* [x] Verification Service

Acceptance:

Execution verified.

---

# 15. Phase 9

## Rollback Platform

Timeline:

Week 12–14

Goal:

Recovery.

---

### Components

Checkpoint Manager

Rollback Manager

---

### Storage

MinIO

Snapshots

Artifacts

---

## Checklist

* [x] Snapshot Service
* [x] Rollback Service

Acceptance:

State restored.

---

# 16. Phase 10

## Kafka Backbone

Timeline:

Week 14–16

Goal:

Distributed runtime.

---

### Topics

runtime-events

telemetry-events

rollback-events

verification-events

policy-events

---

## Checklist

* [x] Kafka Cluster
* [x] Producer SDK
* [x] Consumer SDK

Acceptance:

Streaming operational.

---

# 17. Phase 11

## Policy Platform

Timeline:

Week 16–18

Goal:

Govern execution.

---

### Actions

ALLOW

DENY

SANDBOX

APPROVAL_REQUIRED

---

### Human Approval

Agent

↓

Approval

↓

Human

↓

Execution

---

## Checklist

* [x] Policy Engine
* [x] Approval Workflow

Acceptance:

Governance operational.

---

# 18. Phase 12

## State Engine

Timeline:

Month 6

Goal:

Track execution evolution.

---

### Components

State Snapshots

State Hashing

State Lineage

---

### Storage

Qdrant

---

## Checklist

* [x] State Service
* [x] Hash Engine
* [x] Lineage Engine

Acceptance:

State history available.

---

# 19. Phase 13

## Intelligence Layer

Timeline:

Month 8+

Goal:

Use models to improve runtime decisions.

---

### Model Gateway

Providers:

Qwen

DeepSeek

Future Custom Models

---

### Use Cases

Risk Explanation

Policy Explanation

State Analysis

Execution Summaries

---

## Checklist

* [x] Model Gateway
* [x] Qwen Provider
* [x] DeepSeek Provider

Acceptance:

Model-assisted runtime intelligence.

---

# 20. Phase 14

## Enterprise Platform

Timeline:

Month 8–12

---

### Security

RBAC

SSO

Audit Logs

API Keys

---

### Multi-Tenancy

Tenant Isolation

Resource Quotas

Billing

---

### Reliability

Backups

HA

Disaster Recovery

---

## Checklist

* [x] RBAC
* [x] Multi-Tenancy
* [x] DR

Acceptance:

Enterprise-ready deployment.

---

# Definition of Done

A developer installs:

```bash
pip install cri-sdk
```

Then:

```python
runtime.attach(agent)
```

and instantly gains:

* Action Interception
* Risk Analysis
* Telemetry
* Dashboard Visibility
* Sandboxing
* Verification
* Rollback
* Policy Enforcement

without changing how their agent works.

---

# End State

CRI becomes:

* Kubernetes for Autonomous Systems
* OpenTelemetry for Agent Execution
* Control Plane for AI Agents
* Runtime Operating Layer for Autonomous Systems

Not another agent framework.
