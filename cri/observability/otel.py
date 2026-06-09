from __future__ import annotations

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

def init_tracer(service_name: str = "cri-runtime") -> trace.Tracer:
    """
    Initializes and returns a globally registered OpenTelemetry tracer.
    Spans are exported asynchronously to the OTel Collector.
    """
    # Create resource description
    resource = Resource.create(attributes={
        "service.name": service_name,
        "environment": os.getenv("CRI_ENV", "development")
    })
    
    provider = TracerProvider(resource=resource)
    
    # Configure OTLP HTTP trace exporter (connecting to standard local port 4318)
    collector_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    
    try:
        exporter = OTLPSpanExporter(endpoint=collector_endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
    except Exception as exc:
        print(f"OTel Exporter failed to initialize: {exc}. Falling back to console logging processor.")
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

# Expose a default tracer instance
default_tracer = init_tracer()
