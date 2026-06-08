from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from cri_runtime.classifiers import ActionClassifier, classify_shell
from cri_runtime.cognition_os import CognitionOperatingSystem
from cri_runtime.events import EventReplayEngine, TraceManager
from cri_runtime.interception import intercept
from cri_runtime.io import read_file, run_shell, write_file
from cri_runtime.kafka import DEFAULT_TOPICS
from cri_runtime.kubernetes import KubernetesExecutionFabric
from cri_runtime.monitoring import collect_snapshot, snapshot_to_dict
from cri_runtime.multi_agent import MultiAgentRuntime
from cri_runtime.rollback import DistributedRollbackManager
from cri_runtime.runtime import LocalLangGraphRuntime
from cri_runtime.sandbox import SandboxPoolManager
from cri_runtime.state import build_state, semantic_state_hash
from cri_runtime.telemetry import TelemetryEmitter
from cri_runtime.verification import VerificationEngine


@intercept("task")
def handle_task(task: str) -> int:
    state = build_state(task, active_files=["main.py", "pyproject.toml", "docker-compose.yml"])
    emitter = TelemetryEmitter()
    try:
        state_hash = semantic_state_hash(state)
        emitter.emit({"event_type": "task_received", "payload": {"task": task, "semantic_state_hash": state_hash}})
        print("semantic_state_hash:", state_hash)
        print("plan:")
        print("-", f"Received task: {task}")
        print("-", "Inspect package requirements" if "install" in task.lower() else "Review requested changes")
        print("-", "Report semantic state hash and execution plan")
        return 0
    finally:
        emitter.close()


@intercept("read_file")
def handle_read(path: str) -> None:
    print(read_file(path))


@intercept("write_file")
def handle_write(path: str, content: str) -> None:
    write_file(path, content)
    print(f"Wrote {path}")


@intercept("run_shell")
def handle_run(command: str) -> None:
    print(json.dumps(run_shell(command), indent=2))


@intercept("classify_python")
def handle_classify_python(source: str) -> None:
    classifier = ActionClassifier()
    print(json.dumps(classifier.classify(source), indent=2))


@intercept("classify_shell")
def handle_classify_shell(command: str) -> None:
    print(json.dumps(classify_shell(command), indent=2))


@intercept("sandbox_exec")
def handle_sandbox(command: str) -> None:
    manager = SandboxPoolManager()
    claim = manager.claim()
    print(json.dumps(manager.exec_in_sandbox(claim, command), indent=2))


@intercept("agent_run")
def handle_agent(task: str) -> None:
    runtime = LocalLangGraphRuntime(trace_manager=TraceManager())
    state = runtime.run(task, active_files=["main.py", "pyproject.toml", "docker-compose.yml"])
    print(json.dumps(state, indent=2))


@intercept("event_replay")
def handle_replay(path: str | None) -> None:
    if path:
        events = EventReplayEngine().replay(path)
    else:
        events = TraceManager().replay()
    print(json.dumps(events, indent=2))


@intercept("verify")
def handle_verify(task: str) -> None:
    runtime = LocalLangGraphRuntime()
    state = runtime.run(task, active_files=["main.py", "pyproject.toml", "docker-compose.yml"])
    result = VerificationEngine().verify_execution_history(state["execution_history"])
    print(json.dumps(asdict(result), indent=2))


@intercept("multi_agent")
def handle_multi_agent(task: str) -> None:
    result = MultiAgentRuntime().run(task)
    print(json.dumps(result, indent=2))


@intercept("topics")
def handle_topics() -> None:
    print(json.dumps([asdict(topic) for topic in DEFAULT_TOPICS], indent=2))


@intercept("rollback_demo")
def handle_rollback_demo(task: str) -> None:
    runtime = LocalLangGraphRuntime()
    state = runtime.run(task, active_files=["main.py", "pyproject.toml", "docker-compose.yml"])
    manager = DistributedRollbackManager()
    checkpoint = manager.create_checkpoint(state, "manual rollback demo")
    restored = manager.restore(checkpoint.checkpoint_id)
    print(json.dumps({"checkpoint": asdict(checkpoint), "restored": restored}, indent=2))


@intercept("k8s_plan")
def handle_k8s_plan() -> None:
    print(json.dumps(KubernetesExecutionFabric().plan(), indent=2))


@intercept("cognition_os")
def handle_cognition_os(task: str) -> None:
    print(json.dumps(CognitionOperatingSystem().run(task), indent=2))


@intercept("serve")
def handle_serve(host: str, port: int) -> None:
    import uvicorn

    uvicorn.run("cri_runtime.api:app", host=host, port=port, reload=False)


@intercept("monitor")
def handle_monitor(task: str) -> None:
    active_files = ["main.py", "pyproject.toml", "docker-compose.yml", "grafana/dashboards/cri-runtime-dashboard.json"]
    snapshot = collect_snapshot(task, active_files=active_files)
    print(json.dumps(snapshot_to_dict(snapshot), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cri-runtime", description="CRI Runtime Phase 1 MVP scaffold")
    parser.add_argument("--task", help="Task prompt for the agent")
    parser.add_argument("--read", help="Read a local file")
    parser.add_argument("--write", nargs=2, metavar=("PATH", "CONTENT"), help="Write content to a local file")
    parser.add_argument("--run", help="Run a shell command")
    parser.add_argument("--sandbox", help="Run a shell command inside a sandbox claim")
    parser.add_argument("--agent", help="Run the baseline autonomous agent runtime for a task")
    parser.add_argument("--replay", nargs="?", const="", help="Replay runtime trace events, or a supplied JSONL event path")
    parser.add_argument("--verify", help="Run a task and verify its execution history")
    parser.add_argument("--multi-agent", dest="multi_agent", help="Run the task through the multi-agent coordinator")
    parser.add_argument("--topics", action="store_true", help="Print Kafka topic definitions")
    parser.add_argument("--rollback-demo", help="Run a task and demonstrate checkpoint restore")
    parser.add_argument("--k8s-plan", action="store_true", help="Print the Kubernetes execution fabric plan")
    parser.add_argument("--cognition-os", help="Run the full cognition OS coordinator for a task")
    parser.add_argument("--serve", action="store_true", help="Start the CRI Runtime HTTP service")
    parser.add_argument("--host", default="127.0.0.1", help="Host for --serve")
    parser.add_argument("--port", type=int, default=8000, help="Port for --serve")
    parser.add_argument("--monitor", help="Print a monitoring snapshot for the current task")
    parser.add_argument("--classify-python", dest="classify_python", help="Classify Python source risk from a string")
    parser.add_argument("--classify-shell", dest="classify_shell", help="Classify shell command risk")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.read:
        handle_read(args.read)
        return
    if args.write:
        handle_write(args.write[0], args.write[1])
        return
    if args.run:
        handle_run(args.run)
        return
    if args.sandbox:
        handle_sandbox(args.sandbox)
        return
    if args.agent:
        handle_agent(args.agent)
        return
    if args.replay is not None:
        handle_replay(args.replay or None)
        return
    if args.verify:
        handle_verify(args.verify)
        return
    if args.multi_agent:
        handle_multi_agent(args.multi_agent)
        return
    if args.topics:
        handle_topics()
        return
    if args.rollback_demo:
        handle_rollback_demo(args.rollback_demo)
        return
    if args.k8s_plan:
        handle_k8s_plan()
        return
    if args.cognition_os:
        handle_cognition_os(args.cognition_os)
        return
    if args.serve:
        handle_serve(args.host, args.port)
        return
    if args.monitor:
        handle_monitor(args.monitor)
        return
    if args.classify_python:
        handle_classify_python(args.classify_python)
        return
    if args.classify_shell:
        handle_classify_shell(args.classify_shell)
        return
    if args.task:
        raise SystemExit(handle_task(args.task))

    parser.print_help()


if __name__ == "__main__":
    main()
