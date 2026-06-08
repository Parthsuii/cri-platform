from __future__ import annotations

import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "main.py", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_agent_runs_direct_shell_command() -> None:
    result = run_cli("--agent", "run echo hello")

    assert result.returncode == 0
    assert "Intercepted: agent_run" in result.stdout
    assert '"route": "direct"' in result.stdout
    assert '"stdout": "hello\\n"' in result.stdout


def test_verify_reports_passed_execution() -> None:
    result = run_cli("--verify", "run echo verified")

    assert result.returncode == 0
    assert '"passed": true' in result.stdout
    assert '"failures": []' in result.stdout


def test_risky_shell_command_routes_to_sandbox() -> None:
    result = run_cli("--agent", "run rm temp.txt")

    assert result.returncode == 0
    assert '"route": "sandbox"' in result.stdout
    assert "forbidden shell command: rm" in result.stdout


def test_kubernetes_plan_lists_runtime_job() -> None:
    result = run_cli("--k8s-plan")

    assert result.returncode == 0
    assert '"fabric": "kubernetes"' in result.stdout
    assert '"path": "k8s/runtime-job.yaml"' in result.stdout


def test_cognition_os_coordinates_verification_and_rollback() -> None:
    result = run_cli("--cognition-os", "run echo cognition")

    assert result.returncode == 0
    assert '"checkpoint_id": "rollback-1"' in result.stdout
    assert '"passed": true' in result.stdout
    assert '"contradictions": []' in result.stdout
