from __future__ import annotations

from cri_runtime.api import app

if __name__ == "__main__":
    import uvicorn
    # Start the API Gateway on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
