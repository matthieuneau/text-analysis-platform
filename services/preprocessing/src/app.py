import os

import uvicorn
from fastapi import FastAPI
from logger import configure_logging, get_logger

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from routes import router


# Initialize tracing
def setup_tracing():
    trace.set_tracer_provider(TracerProvider())

    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317"),
        insecure=True,
    )

    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)


setup_tracing()

configure_logging()

logger = get_logger(__name__)

app = FastAPI(
    title="Text Preprocessing Service",
    description="Microservice for text cleaning, tokenization, and normalization",
    version="1.0.0",
)

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
# Auto-instrument requests (if you make HTTP calls to other services)
RequestsInstrumentor().instrument()

app.include_router(router)


if __name__ == "__main__":
    # For development only - use gunicorn for production
    uvicorn.run(app, host="0.0.0.0", port=8000)
