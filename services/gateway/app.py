import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

import httpx
import structlog
import uvicorn
from config import settings
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# Configure structured logging
def setup_logging():
    """Configure structured logging"""
    if settings.log_format == "json":
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        # Simple text logging for development
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=getattr(logging, settings.log_level.upper()),
            stream=sys.stdout,
        )

    return structlog.get_logger()


# Global HTTP client
http_client: httpx.AsyncClient | None = None
logger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global http_client, logger

    # Setup logging
    logger = setup_logging()
    logger.info("Starting Text Analysis Gateway", version=settings.version)

    # Initialize HTTP client
    timeout = httpx.Timeout(
        connect=settings.connection_timeout,
        read=settings.read_timeout,
        write=10.0,
        pool=5.0,
    )

    limits = httpx.Limits(
        max_keepalive_connections=settings.connection_pool_size,
        max_connections=settings.connection_pool_size + 10,
    )

    http_client = httpx.AsyncClient(
        timeout=timeout, limits=limits, follow_redirects=True
    )

    logger.info("HTTP client initialized")

    # Check service health on startup
    await check_all_services_health()

    logger.info("Gateway startup completed successfully")

    yield

    # Shutdown
    logger.info("Shutting down Text Analysis Gateway")
    if http_client:
        await http_client.aclose()
    logger.info("Gateway shutdown completed")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API Gateway for Text Analysis Microservices",
    lifespan=lifespan,
    debug=settings.debug,
)

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
    start_time = structlog.get_logger().info

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


# Helper functions
async def make_service_request(
    service_config,
    endpoint: str,
    method: str = "GET",
    json_data: Dict = None,
    params: Dict = None,
) -> Dict[str, Any]:
    """Make a request to a service with retry logic"""
    url = f"{service_config.url.rstrip('/')}/{endpoint.lstrip('/')}"

    for attempt in range(service_config.max_retries + 1):
        try:
            if method.upper() == "GET":
                response = await http_client.get(
                    url, params=params, timeout=service_config.timeout
                )
            elif method.upper() == "POST":
                response = await http_client.post(
                    url, json=json_data, params=params, timeout=service_config.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            logger.warning(
                "Service request timeout",
                url=url,
                attempt=attempt + 1,
                max_attempts=service_config.max_retries + 1,
            )
            if attempt == service_config.max_retries:
                raise HTTPException(status_code=504, detail=f"Service timeout: {url}")

        except httpx.HTTPStatusError as e:
            logger.warning(
                "Service returned error status",
                url=url,
                status_code=e.response.status_code,
                attempt=attempt + 1,
            )
            if attempt == service_config.max_retries:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Service error: {e.response.text}",
                )

        except Exception as e:
            logger.error(
                "Service request failed", url=url, error=str(e), attempt=attempt + 1
            )
            if attempt == service_config.max_retries:
                raise HTTPException(
                    status_code=503, detail=f"Service unavailable: {url}"
                )

        # Wait before retry
        if attempt < service_config.max_retries:
            import asyncio

            wait_time = service_config.retry_backoff * (2**attempt)
            await asyncio.sleep(wait_time)


async def check_service_health(service_name: str, service_config) -> Dict[str, Any]:
    """Check health of a single service"""
    try:
        result = await make_service_request(service_config, "health", "GET")
        return {
            "service": service_name,
            "status": "healthy",
            "url": service_config.url,
            "response": result,
        }
    except Exception as e:
        return {
            "service": service_name,
            "status": "unhealthy",
            "url": service_config.url,
            "error": str(e),
        }


async def check_all_services_health() -> Dict[str, Any]:
    """Check health of all services"""
    services = {
        "preprocessing": settings.preprocessing_service,
        "sentiment": settings.sentiment_service,
        "summarization": settings.summarization_service,
    }

    results = {}
    for service_name, service_config in services.items():
        results[service_name] = await check_service_health(service_name, service_config)

    return results


# Health check endpoints
@app.get("/health")
async def gateway_health():
    """Gateway health check"""
    return {"status": "healthy", "service": "gateway", "version": settings.version}


@app.get("/services/status")
async def services_status():
    """Check status of all backend services"""
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


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
