# CRI Runtime - Phase 1 MVP Master Specification
**Version:** 1.1 (Final - Development Ready)
**Objective:** Deliver the End-to-End Interception & Streaming Loop.

This document serves as the master blueprint for the engineering team to build the Phase 1 CRI Runtime. It translates architectural constraints into actionable epics, tickets, and code-level acceptance criteria.

---

## 1. Architecture Topology

```text
+------------------------------------------------------+
| CLI Entry Point (main.py)                            |
+------------------------------------------------------+
                     |
                     v
+------------------------------------------------------+
| Autonomous Coding Agent (Epic 1)                     |
| - LangGraph planner | OpenAI/Claude interface        |
+------------------------------------------------------+
                     |
                     v
+------------------------------------------------------+
| CRI Interceptor Layer (Epic 2 & 3)                   |
| - AST Risk Classification                            |
| - Tripartite State Hashing                           |
+------------------------------------------------------+
                     |
         +-----------+------------+
         |                        |
         v                        v
+------------------+    +-------------------------+
| Safe Execution   |    | Pre-Warmed Sandbox Pool |
|                  |    | (Epic 5)                |
| Direct execution |    | Sub-300ms isolation     |
+------------------+    +-------------------------+
                     |
                     v
+------------------------------------------------------+
| Async Telemetry Ring Buffer (Epic 4)                 |
| - Local memory queue (fire-and-forget for agent)     |
| - Background worker flushes to Kafka (acks=all)      |
| - Local WAL fallback for zero data loss              |
+------------------------------------------------------+
                     |
                     v
+------------------------------------------------------+
| Kafka Event Backbone (Epic 4)                        |
| - Topics: cognitive-events, runtime-events           |
+------------------------------------------------------+
                     |
                     v
+------------------------------------------------------+
| Java Ingestion Service (Epic 6)                      |
| - Spring Boot + PostgreSQL (JSONB)                   |
+------------------------------------------------------+
                     |
                     v
+------------------------------------------------------+
| Observability Dashboard (Epic 7)                     |
| - Grafana connected live to PostgreSQL               |
+------------------------------------------------------+
```

---

## 2. Global Setup & Standards

### Task 0.1: Repository & Secrets Management
* **Description:** Initialize the monorepo, define dependency management (e.g., `poetry` for Python, `gradle`/`maven` for Java), and establish a strict `.env` pattern for secrets. **Do not hardcode API keys.**
* **AC:** Engineers can pull the repo, copy `.env.example` to `.env`, populate `OPENAI_API_KEY` and `POSTGRES_PASSWORD`, and run `docker-compose up -d`.

### Task 0.2: Define CLI Entry Point
* **Description:** The system must be triggered via a simple CLI for Phase 1. No frontends.
* **AC:** Agent is invoked via terminal: `python main.py --task "install requests and write a script to fetch google.com"`

---

## Epic 1: The Baseline Unstable Agent
**Goal:** Build the chaotic intelligence engine that we will subsequently constrain. The runtime only matters if the agent can fail.

### Task 1.1: Stand up LangGraph Base & State Management
* **Description:** Initialize LangGraph orchestration and connect to the LLM. 
* **State Definition:**
  ```python
  from typing import TypedDict, List, Any
  class AgentState(TypedDict):
      messages: List[Any]
      current_goal: str
      active_files: List[str]
      execution_history: List[dict]
      retries: int
  ```
* **AC:** Agent can receive a prompt via CLI and output a planned sequence of actions.

### Task 1.2: Implement Shell & File Tools
* **Description:** Build raw `read_file`, `write_file`, and `run_shell` tools. **Do not secure them.**
* **AC:** Agent can successfully read/write to the local filesystem and execute terminal commands.

### Task 1.3: Induce Instability (Testing Harness)
* **Description:** Write a set of test prompts designed to make the agent hallucinate package names or attempt to delete critical files.
* **AC:** Agent demonstrably attempts dangerous actions (e.g., `os.remove`, `pip install fake-package`).

---

## Epic 2: The AST Action Interceptor
**Goal:** Intercept all cognition and mathematically classify risk, moving beyond brittle string matching.

### Task 2.1: Interceptor Middleware Routing
* **Description:** Force all LangGraph tool calls through a central Python decorator/middleware before execution.
* **AC:** 100% of tool executions trigger a console log: `Intercepted: [Action]` before running.

### Task 2.2: Implement Python AST Risk Classifier
* **Description:** Build an `ActionClassifier(ast.NodeVisitor)` to parse Python syntax and flag forbidden operations.
  * Deny `imports`: `os`, `subprocess`, `shutil`, `sys`, `socket`.
  * Deny `calls`: `open`, `exec`, `eval`, `__import__`, `os.system`, `os.remove`.
* **AC:** Classifier successfully flags obfuscated/aliased dangerous Python code as "HIGH" risk.

### Task 2.3: Implement Shell/Regex Risk Classifier
* **Description:** Build POSIX tokenization to flag dangerous bash commands.
* **AC:** Classifier flags shell commands (`rm`, `chmod`, `mv`) as "HIGH" risk, regardless of flag placement (e.g., `rm -rf /` vs `rm / -rf`).

---

## Epic 3: Tripartite Semantic Hashing
**Goal:** Create the deterministic state ID required for future rollbacks.

### Task 3.1: Build State Normalizer & Hasher
* **Description:** Implement logic to create a deterministic hash of the agent's current state.
  1.  **Normalize Memory:** Strip timestamps/latency metrics from execution history.
  2.  **Normalize Workspace:** Create an MD5 hash dictionary of all active files, sorted alphabetically.
  3.  **Hash Generation:** Combine normalized memory, workspace, and goal into a strict JSON string (no whitespace, sorted keys) and compute the SHA-256 hash.
* **AC:** Running the agent twice on the exact same task produces the identical `semantic_state_hash` output.

---

## Epic 4: Asynchronous Telemetry Ring Buffer & Kafka
**Goal:** Stream data to Kafka without blocking the LLM, ensuring zero data loss.

### Task 4.1: Stand up Local Kafka (Docker Compose)
* **Description:** Initialize Confluent Kafka locally using the provided `docker-compose.yml`.
* **AC:** Kafka is accessible on `localhost:9092` with topics: `cognitive-events`.

### Task 4.2: Build the LMAX-style Ring Buffer Daemon
* **Description:** Implement a `TelemetryEmitter`. The main agent thread pushes events to an in-memory `queue.Queue` (fire-and-forget). A background daemon thread reads the queue and publishes to Kafka with `acks='all'`.
* **AC:** Agent execution time does not increase by more than 5ms when telemetry is emitted.

### Task 4.3: Local Write-Ahead Log (WAL) Fallback
* **Description:** If the in-memory queue fills up or Kafka is unreachable, write the JSON telemetry to a local file (`/var/log/cri/telemetry_crash.log`).
* **AC:** Shutting down Kafka while the agent runs results in telemetry successfully writing to local disk.

---

## Epic 5: Pre-Warmed Docker Sandbox
**Goal:** Sub-300ms isolation execution latency for HIGH-risk actions. Cold starts are forbidden.

### Task 5.1: Create Sandbox Docker Image
* **Description:** Build a lightweight `cri-sandbox-base` Dockerfile containing Python.
* **AC:** Image builds locally and runs securely (`network_mode="none"`).

### Task 5.2: Implement SandboxPoolManager
* **Description:** Build a Python queue manager that continuously runs a configurable number of idle containers.
* **AC:** System maintains exactly 3 idle `cri-sandbox-base` containers running in the background at all times.

### Task 5.3: Container Claim & Async Teardown Logic
* **Description:** When a "HIGH" risk action is intercepted, route it to an idle container using `docker exec`. Capture output. Asynchronously destroy and replace the container.
* **AC:** Time from intercepting a dangerous command to execution start inside the container is `<300ms`.

---

## Epic 6: Java Ingestion Engine
**Goal:** Persist the data asynchronously for high-throughput enterprise scalability.

### Task 6.1: Spring Boot Kafka Consumer
* **Description:** Stand up a Java Spring Boot service with `@KafkaListener` subscribed to `cognitive-events`.
* **AC:** Java service logs received telemetry JSON to the console.

### Task 6.2: PostgreSQL Persistence
* **Description:** Connect Spring Boot to PostgreSQL. Define a JPA entity to persist the incoming JSON payload into a `JSONB` column.
* **AC:** Telemetry is durably queryable via SQL (`SELECT * FROM cognitive_events`).

---

## Epic 7: Day 14 Demo Assembly & Observability
**Goal:** Prove the end-to-end loop to stakeholders visually.

### Task 7.1: Grafana Configuration
* **Description:** Spin up Grafana in Docker, connect it to the PostgreSQL database as a data source.
* **AC:** Create a dashboard showing "Total Cognition Events", "High Risk Actions Blocked", and a live table of the agent's thought stream.

### Task 7.2: End-to-End Integration Demo
* **Description:** Connect all components and run the live presentation.
* **AC:** Successful recording of a fully isolated, logged, and persisted hallucination execution:
  1. CLI triggers Agent.
  2. Agent proposes `os.remove`.
  3. AST blocks it (Epic 2).
  4. Action executes safely in Sandbox (Epic 5) in <300ms.
  5. Telemetry streams async to Kafka (Epic 4).
  6. Data persists in Postgres (Epic 6).
  7. Event flashes live on Grafana dashboard (Epic 7).

---

## Appendix A: Foundational `docker-compose.yml`
*Give this to DevOps on Day 1.*

```yaml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.3.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:7.3.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: cri_admin
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-supersecret}
      POSTGRES_DB: cri_runtime
    ports:
      - "5432:5432"

  grafana:
    image: grafana/grafana:latest
    depends_on:
      - postgres
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## Appendix B: `.env.example`
```env
# Agent Runtime Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...

# Infrastructure
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
POSTGRES_USER=cri_admin
POSTGRES_PASSWORD=supersecret
POSTGRES_URL=jdbc:postgresql://localhost:5432/cri_runtime
```
