from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable
from fastapi import FastAPI, Request, Response

class StructuredLogger:
    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        # Configure standard logging to output to console
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        self.logger = logging.getLogger(service_name)

    def log(self, level: str, message: str, extra: dict[str, Any] | None = None) -> None:
        payload = {
            "timestamp": time.time(),
            "service": self.service_name,
            "level": level.upper(),
            "message": message,
            **(extra or {})
        }
        self.logger.info(json.dumps(payload))

    def info(self, message: str, extra: dict[str, Any] | None = None) -> None:
        self.log("INFO", message, extra)

    def error(self, message: str, extra: dict[str, Any] | None = None) -> None:
        self.log("ERROR", message, extra)

class MetricsCollector:
    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self.request_count = 0
        self.error_count = 0
        self.total_latency = 0.0

    def record_request(self, latency: float, success: bool) -> None:
        self.request_count += 1
        self.total_latency += latency
        if not success:
            self.error_count += 1

    def to_prometheus_format(self) -> str:
        avg_latency = (self.total_latency / self.request_count) if self.request_count > 0 else 0.0
        return (
            f"# HELP cri_{self.service_name}_requests_total Total number of actions/requests processed\n"
            f"# TYPE cri_{self.service_name}_requests_total counter\n"
            f"cri_{self.service_name}_requests_total {self.request_count}\n"
            f"# HELP cri_{self.service_name}_errors_total Total number of failed requests\n"
            f"# TYPE cri_{self.service_name}_errors_total counter\n"
            f"cri_{self.service_name}_errors_total {self.error_count}\n"
            f"# HELP cri_{self.service_name}_avg_latency_seconds Average request execution latency in seconds\n"
            f"# TYPE cri_{self.service_name}_avg_latency_seconds gauge\n"
            f"cri_{self.service_name}_avg_latency_seconds {avg_latency:.6f}\n"
        )

def setup_service(service_name: str) -> tuple[FastAPI, StructuredLogger, MetricsCollector]:
    app = FastAPI(title=f"CRI {service_name.replace('_', ' ').title()} Service")
    logger = StructuredLogger(service_name)
    metrics = MetricsCollector(service_name)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        success = True
        try:
            response = await call_next(request)
            if response.status_code >= 400:
                success = False
            return response
        except Exception as exc:
            success = False
            raise exc from None
        finally:
            latency = time.time() - start_time
            # Exclude /health and /metrics from analytics counters
            if request.url.path not in ["/health", "/metrics"]:
                metrics.record_request(latency, success)
                logger.info(f"Processed request: {request.method} {request.url.path}", {
                    "method": request.method,
                    "path": request.url.path,
                    "latency_seconds": latency,
                    "success": success
                })

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": service_name}

    @app.get("/metrics")
    def get_metrics() -> Response:
        return Response(content=metrics.to_prometheus_format(), media_type="text/plain")

    return app, logger, metrics
