from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from orchestrator.compiler import AppCompiler
from .service import RuntimeService

compiler = AppCompiler()
compilation_history: list[dict[str, object]] = []

class CompileRequest(BaseModel):
    prompt: str = Field(min_length=1)


class TaskRequest(BaseModel):
    task: str = Field(min_length=1)
    mode: Literal["agent", "cognition_os"] = "cognition_os"


class RollbackRequest(BaseModel):
    checkpoint_id: str = Field(min_length=1)


service = RuntimeService()
app = FastAPI(title="CRI Runtime Service", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/api")
def api_info() -> dict[str, object]:
    return {
        "name": "CRI Runtime Service",
        "status": "ok",
        "docs": "/docs",
        "endpoints": [
            "GET /health",
            "POST /tasks",
            "GET /tasks",
            "GET /tasks/{task_id}",
            "GET /trace",
            "POST /rollback",
            "GET /k8s/plan",
        ],
        "example": {
            "method": "POST",
            "path": "/tasks",
            "body": {"task": "run echo hello", "mode": "agent"},
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tasks")
def submit_task(request: TaskRequest) -> dict[str, object]:
    return service.submit_task(request.task, request.mode)


@app.get("/tasks")
def list_tasks() -> list[dict[str, object]]:
    return service.list_tasks()


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, object]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.get("/trace")
def replay_trace() -> list[dict[str, object]]:
    return service.replay_trace()


@app.post("/rollback")
def rollback(request: RollbackRequest) -> dict[str, object]:
    try:
        return service.rollback_task(request.checkpoint_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/k8s/plan")
def k8s_plan() -> dict[str, object]:
    return service.kubernetes_plan()


@app.post("/compiler/compile")
def compile_prompt(request: CompileRequest) -> dict[str, object]:
    try:
        result = compiler.compile(request.prompt)
        res_dict = result.model_dump()
        compilation_history.append(res_dict)
        return res_dict
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/compiler/history")
def get_compiler_history() -> list[dict[str, object]]:
    return compilation_history


@app.get("/compiler/metrics")
def get_compiler_metrics() -> dict[str, object]:
    if not compilation_history:
        return {
            "total_compilations": 0,
            "average_latency_ms": 0,
            "success_rate": 1.0,
            "repair_attempts": 0
        }
    
    total = len(compilation_history)
    total_latency = sum(item["metrics"]["total_time_ms"] for item in compilation_history)
    repairs = sum(item["metrics"]["repair_attempts"] for item in compilation_history)
    successes = sum(item["metrics"]["success_rate"] for item in compilation_history)
    
    return {
        "total_compilations": total,
        "average_latency_ms": int(total_latency / total),
        "success_rate": successes / total,
        "repair_attempts": repairs
    }
