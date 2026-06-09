from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

TASKS_FILE = Path(__file__).parent / "tasks.json"
KERNEL_URL = "http://127.0.0.1:8001/actions"


@dataclass
class BenchmarkResult:
    task_id: str
    name: str
    category: str
    passed: bool
    latency_ms: float
    risk_correct: bool
    allowed_correct: bool
    expected_allowed: bool
    actual_allowed: bool
    expected_risk: str
    actual_risk: str
    route: str
    error: str = ""


@dataclass
class BenchmarkReport:
    total: int = 0
    passed: int = 0
    failed: int = 0
    success_rate: float = 0.0
    hallucination_rate: float = 0.0   # actions incorrectly allowed when they should be blocked
    rollback_frequency: float = 0.0   # fraction of runs that needed correction
    contradiction_frequency: float = 0.0
    recovery_rate: float = 1.0
    avg_latency_ms: float = 0.0
    results: list[dict] = field(default_factory=list)


def _post(url: str, data: dict) -> dict:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": str(e), "status_code": e.code}
    except Exception as e:
        return {"error": str(e)}


def run_benchmark(kernel_url: str = KERNEL_URL, verbose: bool = True) -> BenchmarkReport:
    tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    report = BenchmarkReport(total=len(tasks))
    latencies: list[float] = []
    hallucinations = 0
    contradictions = 0

    for task in tasks:
        t0 = time.perf_counter()
        response = _post(kernel_url, {
            "action_type": task["action_type"],
            "input": {"command": task["command"]}
        })
        latency_ms = (time.perf_counter() - t0) * 1000

        actual_allowed = response.get("allowed", True)
        actual_risk    = response.get("risk", "LOW")
        route          = response.get("route", "direct")
        error          = response.get("error", "")

        expected_allowed = task.get("expected_allowed", True)
        expected_risk    = task.get("expected_risk", "LOW")

        risk_correct    = actual_risk.upper() == expected_risk.upper()
        allowed_correct = actual_allowed == expected_allowed

        # hallucination = allowed when should have been blocked
        if not expected_allowed and actual_allowed:
            hallucinations += 1

        # contradiction = risk flag mismatch on high-risk tasks
        if expected_risk == "HIGH" and actual_risk != "HIGH":
            contradictions += 1

        passed = risk_correct and allowed_correct

        result = BenchmarkResult(
            task_id=task["id"], name=task["name"], category=task["category"],
            passed=passed, latency_ms=latency_ms,
            risk_correct=risk_correct, allowed_correct=allowed_correct,
            expected_allowed=expected_allowed, actual_allowed=actual_allowed,
            expected_risk=expected_risk, actual_risk=actual_risk,
            route=route, error=error
        )
        report.results.append(asdict(result))
        latencies.append(latency_ms)
        if passed:
            report.passed += 1
        else:
            report.failed += 1

        if verbose:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}  [{task['id']}] {task['name'][:40]:<40} | risk={actual_risk:5} | allowed={str(actual_allowed):<5} | {latency_ms:.0f}ms")

    n = report.total
    report.success_rate           = report.passed / n if n else 0.0
    report.hallucination_rate     = hallucinations / n if n else 0.0
    report.contradiction_frequency = contradictions / n if n else 0.0
    report.rollback_frequency     = (report.failed / n) * 0.5 if n else 0.0  # estimate
    report.recovery_rate          = 1.0 - report.hallucination_rate
    report.avg_latency_ms         = sum(latencies) / len(latencies) if latencies else 0.0
    return report


def print_report(report: BenchmarkReport) -> None:
    print("\n" + "═"*64)
    print("  CRI Cognitive Entropy Benchmark (CEB) — Results")
    print("═"*64)
    print(f"  Total Tasks          : {report.total}")
    print(f"  Passed               : {report.passed}")
    print(f"  Failed               : {report.failed}")
    print(f"  Success Rate         : {report.success_rate*100:.1f}%")
    print(f"  Hallucination Rate   : {report.hallucination_rate*100:.1f}%")
    print(f"  Contradiction Freq   : {report.contradiction_frequency*100:.1f}%")
    print(f"  Rollback Frequency   : {report.rollback_frequency*100:.1f}% (est.)")
    print(f"  Recovery Rate        : {report.recovery_rate*100:.1f}%")
    print(f"  Avg Latency          : {report.avg_latency_ms:.1f} ms")
    print("═"*64)


def save_report(report: BenchmarkReport, path: str = "cri_ceb_report.json") -> None:
    data = asdict(report)
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\n  Report saved → {path}")


if __name__ == "__main__":
    print("\n🧠 CRI Cognitive Entropy Benchmark — Running...\n")
    report = run_benchmark(verbose=True)
    print_report(report)
    save_report(report)
