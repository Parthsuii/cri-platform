from __future__ import annotations

import subprocess
import sys
from fastapi import FastAPI, Body
from pydantic import BaseModel
from packages.shared.service_utils import setup_service

app, logger, metrics = setup_service("sandbox")

class ExecutionOutput(BaseModel):
    stdout: str
    stderr: str
    returncode: int

@app.post("/execute", response_model=ExecutionOutput)
def execute(payload: dict = Body(...)) -> ExecutionOutput:
    command = str(payload.get("command", ""))
    logger.info("Executing command in sandbox environment", {"command": command})
    
    # We execute command in isolated subprocess to mock docker runtime controls
    try:
        # On Windows shell is required for cmd commands
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return ExecutionOutput(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode
        )
    except subprocess.TimeoutExpired:
        return ExecutionOutput(
            stdout="",
            stderr="Execution timed out in sandbox container",
            returncode=-1
        )
    except Exception as exc:
        return ExecutionOutput(
            stdout="",
            stderr=str(exc),
            returncode=-1
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
