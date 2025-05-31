import time

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from routes import router
from settings import settings
from utils import (
    check_all_services_health,
    get_logger,  # Import the getter function instead
    lifespan,
    make_service_request,
)

# Prometheus metrics
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
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API Gateway for Text Analysis Microservices",
    lifespan=lifespan,
    debug=settings.debug,
)

app.include_router(router)


def get_endpoint_path(request: Request) -> str:
    """Extract a clean endpoint path for metrics"""
    path = request.url.path
    # Group dynamic paths for better metrics
    if path.startswith("/api/"):
        return path
    elif path in ["/health", "/services/status"]:
        return path
    elif path.startswith("/preprocessing/"):
        return "/preprocessing/*"
    elif path.startswith("/sentiment/"):
        return "/sentiment/*"
    elif path.startswith("/summarization/"):
        return "/summarization/*"
    else:
        return "/other"


# Middleware for metrics collection
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect Prometheus metrics for all requests"""
    if request.url.path == "/metrics":
        # Don't track metrics endpoint itself
        return await call_next(request)

    # Track active requests
    ACTIVE_REQUESTS.inc()

    # Get clean endpoint for metrics
    endpoint = get_endpoint_path(request)
    method = request.method

    # Start timing
    start_time = time.time()

    try:
        response = await call_next(request)
        status_code = str(response.status_code)

        # Record metrics
        REQUEST_COUNT.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()

        return response

    except Exception as e:
        # Record error metrics
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code="500").inc()
        raise

    finally:
        # Record request duration
        duration = time.time() - start_time
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        # Decrease active requests
        ACTIVE_REQUESTS.dec()


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    logger = get_logger()  # Get logger when needed

    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
    )

    response = await call_next(request)

    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
    )

    return response


# Exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging"""
    logger = get_logger()  # Get logger when needed

    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
        method=request.method,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger = get_logger()  # Get logger when needed

    logger.error(
        "Unhandled exception occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        url=str(request.url),
        method=request.method,
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={"error": True, "message": "Internal server error", "status_code": 500},
    )


# Health check endpoints
@app.get("/health")
async def gateway_health():
    """Gateway health check"""
    return {"status": "healthy", "service": "gateway", "version": settings.version}


@app.get("/services/status")
async def services_status():
    """Check status of all backend services"""
    logger = get_logger()  # Get logger when needed

    try:
        results = await check_all_services_health()

        # Determine overall status
        all_healthy = all(result["status"] == "healthy" for result in results.values())

        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "services": results,
            "timestamp": structlog.processors.TimeStamper(fmt="iso"),
        }

    except Exception as e:
        logger.error("Failed to check services status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to check services status")


# Basic routing endpoints (pass-through)
@app.get("/preprocessing/health")
async def preprocessing_health():
    """Route to preprocessing service health"""
    return await make_service_request(settings.preprocessing_service, "health", "GET")


@app.get("/sentiment/health")
async def sentiment_health():
    """Route to sentiment service health"""
    return await make_service_request(settings.sentiment_service, "health", "GET")


@app.get("/summarization/health")
async def summarization_health():
    """Route to summarization service health"""
    return await make_service_request(settings.summarization_service, "health", "GET")


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
