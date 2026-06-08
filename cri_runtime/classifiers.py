from __future__ import annotations

import ast
import shlex
from typing import Any


class ActionClassifier(ast.NodeVisitor):
    DENIED_IMPORTS = {"os", "subprocess", "shutil", "sys", "socket"}
    DENIED_CALLS = {"open", "exec", "eval", "__import__", "system", "remove"}

    def __init__(self) -> None:
        self.risk = "LOW"
        self.findings: list[str] = []

    def flag(self, finding: str) -> None:
        self.risk = "HIGH"
        self.findings.append(finding)

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            root = alias.name.split(".", 1)[0]
            if root in self.DENIED_IMPORTS:
                self.flag(f"forbidden import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        module = (node.module or "").split(".", 1)[0]
        if module in self.DENIED_IMPORTS:
            self.flag(f"forbidden import: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        callee = self._callee_name(node.func)
        if callee in self.DENIED_CALLS:
            self.flag(f"forbidden call: {callee}")
        if callee in {"os.system", "os.remove"}:
            self.flag(f"forbidden call: {callee}")
        self.generic_visit(node)

    def _callee_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            left = self._callee_name(node.value)
            return f"{left}.{node.attr}" if left else node.attr
        return ""

    def classify(self, source: str) -> dict[str, Any]:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return {"risk": "HIGH", "findings": [f"syntax error: {exc.msg}"]}
        self.visit(tree)
        return {"risk": self.risk, "findings": self.findings}


def classify_shell(command: str) -> dict[str, Any]:
    tokens = shlex.split(command, posix=True)
    denied = {"rm", "chmod", "mv"}
    findings = [f"forbidden shell command: {token}" for token in tokens if token in denied]
    return {"risk": "HIGH" if findings else "LOW", "findings": findings, "tokens": tokens}
