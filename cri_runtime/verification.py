from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    checks: list[str]
    failures: list[str]


class VerificationEngine:
    def verify_execution_history(self, history: list[dict[str, Any]]) -> VerificationResult:
        checks: list[str] = []
        failures: list[str] = []
        for record in history:
            checks.append(f"{record.get('step')} completed")
            if record.get("status") != "ok":
                failures.append(f"{record.get('step')} status is {record.get('status')}")
            result = record.get("output", {}).get("result")
            if isinstance(result, dict) and result.get("returncode", 0) != 0:
                failures.append(f"{record.get('step')} returned {result.get('returncode')}")
        return VerificationResult(passed=not failures, checks=checks, failures=failures)
