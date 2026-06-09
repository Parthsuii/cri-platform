from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

class CodebaseParser(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: list[str] = []
        self.functions: list[str] = []
        self.calls: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        callee = self._callee_name(node.func)
        if callee:
            self.calls.append(callee)
        self.generic_visit(node)

    def _callee_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            left = self._callee_name(node.value)
            return f"{left}.{node.attr}" if left else node.attr
        return ""

def parse_file(file_path: Path) -> dict[str, Any]:
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        parser = CodebaseParser()
        parser.visit(tree)
        return {
            "file": str(file_path.name),
            "relative_path": str(file_path),
            "imports": parser.imports,
            "functions": parser.functions,
            "calls": parser.calls
        }
    except Exception as exc:
        return {
            "file": str(file_path.name),
            "relative_path": str(file_path),
            "error": str(exc),
            "imports": [],
            "functions": [],
            "calls": []
        }

def scan_repository(repo_path: str) -> list[dict[str, Any]]:
    results = []
    for root, _, files in os.walk(repo_path):
        # Skip hidden and ignore directories
        if any(ignored in root for ignored in {".git", ".venv", "__pycache__", ".pytest_cache", ".gemini"}):
            continue
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                results.append(parse_file(file_path))
    return results
