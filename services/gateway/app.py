import time
import uuid

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from metrics import ACTIVE_REQUESTS, REQUEST_COUNT, REQUEST_DURATION
from prometheus_client import (
    CONTENT_TYPE_LATEST,
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


# Debug tracing middleware - executes first (outermost layer)
@app.middleware("http")
async def debug_trace_middleware(request: Request, call_next):
    """Debug middleware to trace request flow through all middlewares"""
    logger = get_logger()

    # Generate unique request ID for tracing
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start_time = time.time()

    logger.debug(
        "🚀 REQUEST START - Entering debug trace middleware",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        client_ip=request.client.host if request.client else None,
        middleware="debug_trace",
    )

    try:
        response = await call_next(request)

        duration = time.time() - start_time
        logger.debug(
            "✅ REQUEST END - Exiting debug trace middleware",
            request_id=request_id,
            status_code=response.status_code,
            total_duration=f"{duration:.3f}s",
            middleware="debug_trace",
        )

        return response

    except Exception as e:
        duration = time.time() - start_time
        logger.debug(
            "❌ REQUEST ERROR - Exception in debug trace middleware",
            request_id=request_id,
            error=str(e),
            error_type=type(e).__name__,
            total_duration=f"{duration:.3f}s",
            middleware="debug_trace",
        )
        raise


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    logger = get_logger()
    request_id = getattr(request.state, "request_id", "unknown")

    logger.debug(
        "📝 LOGGING - Entering request logging middleware",
        request_id=request_id,
        middleware="log_requests",
    )

    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
    )

    logger.debug(
        "📝 LOGGING - About to call next middleware/handler",
        request_id=request_id,
        middleware="log_requests",
    )

    response = await call_next(request)

    logger.debug(
        "📝 LOGGING - Response received, logging completion",
        request_id=request_id,
        status_code=response.status_code,
        middleware="log_requests",
    )

    logger.info(
        "Request completed",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
    )

    logger.debug(
        "📝 LOGGING - Exiting request logging middleware",
        request_id=request_id,
        middleware="log_requests",
    )

    return response


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for metrics collection
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect Prometheus metrics for all requests"""
    logger = get_logger()
    request_id = getattr(request.state, "request_id", "unknown")

    if request.url.path == "/metrics":
        # Don't track metrics endpoint itself
        logger.debug(
            "📊 METRICS - Skipping metrics collection for /metrics endpoint",
            request_id=request_id,
            middleware="metrics",
        )
        return await call_next(request)

    logger.debug(
        "📊 METRICS - Entering metrics middleware",
        request_id=request_id,
        path=request.url.path,
        middleware="metrics",
    )

    # Track active requests
    ACTIVE_REQUESTS.inc()

    logger.debug(
        "📊 METRICS - Incremented active requests counter",
        request_id=request_id,
        middleware="metrics",
    )

    # Get clean endpoint for metrics
    endpoint = get_endpoint_path(request)
    method = request.method

    # Start timing
    start_time = time.time()

    logger.debug(
        "📊 METRICS - Started timing, about to call next middleware/handler",
        request_id=request_id,
        endpoint=endpoint,
        method=method,
        middleware="metrics",
    )

    try:
        response = await call_next(request)
        status_code = str(response.status_code)

        logger.debug(
            "📊 METRICS - Response received from handler",
            request_id=request_id,
            status_code=status_code,
            middleware="metrics",
        )

        # Record metrics
        REQUEST_COUNT.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()

        logger.debug(
            "📊 METRICS - Recorded request count metric",
            request_id=request_id,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            middleware="metrics",
        )

        return response

    except Exception as e:
        logger.debug(
            "📊 METRICS - Exception occurred, recording error metric",
            request_id=request_id,
            error=str(e),
            middleware="metrics",
        )

        # Record error metrics
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code="500").inc()
        raise

    finally:
        # Record request duration
        duration = time.time() - start_time
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        # Decrease active requests
        ACTIVE_REQUESTS.dec()

        logger.debug(
            "📊 METRICS - Exiting metrics middleware",
            request_id=request_id,
            duration=f"{duration:.3f}s",
            endpoint=endpoint,
            method=method,
            middleware="metrics",
        )


# Exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging"""
    logger = get_logger()
    request_id = getattr(request.state, "request_id", "unknown")

    logger.debug(
        "🚨 EXCEPTION - HTTP exception handler triggered",
        request_id=request_id,
        status_code=exc.status_code,
        detail=exc.detail,
        handler="http_exception",
    )

    logger.error(
        "HTTP exception occurred",
        request_id=request_id,
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
    logger = get_logger()
    request_id = getattr(request.state, "request_id", "unknown")

    logger.debug(
        "🚨 EXCEPTION - General exception handler triggered",
        request_id=request_id,
        error=str(exc),
        error_type=type(exc).__name__,
        handler="general_exception",
    )

    logger.error(
        "Unhandled exception occurred",
        request_id=request_id,
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
    logger = get_logger()

    logger.debug("🏥 HEALTH - Gateway health check endpoint called", endpoint="/health")

    result = {"status": "healthy", "service": "gateway", "version": settings.version}

    logger.debug(
        "🏥 HEALTH - Gateway health check response prepared",
        response=result,
        endpoint="/health",
    )

    return result


@app.get("/services/status")
async def services_status():
    """Check status of all backend services"""
    logger = get_logger()

    logger.debug(
        "🔍 STATUS - Services status endpoint called", endpoint="/services/status"
    )

    try:
        logger.debug(
            "🔍 STATUS - Checking all services health", endpoint="/services/status"
        )

        results = await check_all_services_health()

        logger.debug(
            "🔍 STATUS - Health check results received",
            results=results,
            endpoint="/services/status",
        )

        # Determine overall status
        all_healthy = all(result["status"] == "healthy" for result in results.values())

        response = {
            "overall_status": "healthy" if all_healthy else "degraded",
            "services": results,
            "timestamp": structlog.processors.TimeStamper(fmt="iso"),
        }

        logger.debug(
            "🔍 STATUS - Services status response prepared",
            overall_status=response["overall_status"],
            endpoint="/services/status",
        )

        return response

    except Exception as e:
        logger.debug(
            "🔍 STATUS - Exception occurred while checking services",
            error=str(e),
            endpoint="/services/status",
        )

        logger.error("Failed to check services status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to check services status")


# Basic routing endpoints (pass-through)
@app.get("/preprocessing/health")
async def preprocessing_health():
    """Route to preprocessing service health"""
    logger = get_logger()

    logger.debug(
        "🔄 PROXY - Proxying to preprocessing health endpoint",
        target_service="preprocessing",
        endpoint="/preprocessing/health",
    )

    try:
        result = await make_service_request(
            settings.preprocessing_service, "health", "GET"
        )

        logger.debug(
            "🔄 PROXY - Received response from preprocessing service",
            target_service="preprocessing",
            response=result,
            endpoint="/preprocessing/health",
        )

        return result

    except Exception as e:
        logger.debug(
            "🔄 PROXY - Error proxying to preprocessing service",
            target_service="preprocessing",
            error=str(e),
            endpoint="/preprocessing/health",
        )
        raise


@app.get("/sentiment/health")
async def sentiment_health():
    """Route to sentiment service health"""
    logger = get_logger()

    logger.debug(
        "🔄 PROXY - Proxying to sentiment health endpoint",
        target_service="sentiment",
        endpoint="/sentiment/health",
    )

    try:
        result = await make_service_request(settings.sentiment_service, "health", "GET")

        logger.debug(
            "🔄 PROXY - Received response from sentiment service",
            target_service="sentiment",
            response=result,
            endpoint="/sentiment/health",
        )

        return result

    except Exception as e:
        logger.debug(
            "🔄 PROXY - Error proxying to sentiment service",
            target_service="sentiment",
            error=str(e),
            endpoint="/sentiment/health",
        )
        raise


@app.get("/summarization/health")
async def summarization_health():
    """Route to summarization service health"""
    logger = get_logger()

    logger.debug(
        "🔄 PROXY - Proxying to summarization health endpoint",
        target_service="summarization",
        endpoint="/summarization/health",
    )

    try:
        result = await make_service_request(
            settings.summarization_service, "health", "GET"
        )

        logger.debug(
            "🔄 PROXY - Received response from summarization service",
            target_service="summarization",
            response=result,
            endpoint="/summarization/health",
        )

        return result

    except Exception as e:
        logger.debug(
            "🔄 PROXY - Error proxying to summarization service",
            target_service="summarization",
            error=str(e),
            endpoint="/summarization/health",
        )
        raise


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    logger = get_logger()

    logger.debug("📈 METRICS - Prometheus metrics endpoint called", endpoint="/metrics")

    result = Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    logger.debug(
        "📈 METRICS - Prometheus metrics response generated", endpoint="/metrics"
    )

    return result


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
