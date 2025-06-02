# Prometheus metrics
from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "gateway_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_DURATION = Histogram(
    "gateway_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)
ACTIVE_REQUESTS = Gauge("gateway_active_requests", "Number of active HTTP requests")
SERVICE_UP = Gauge(
    "gateway_service_up", "Service availability (1 = up, 0 = down)", ["service_name"]
)
BACKEND_REQUEST_COUNT = Counter(
    "gateway_backend_requests_total",
    "Total requests to backend services",
    ["service", "endpoint", "status"],
)
BACKEND_REQUEST_DURATION = Histogram(
    "gateway_backend_request_duration_seconds",
    "Backend service request duration",
    ["service", "endpoint"],
)
