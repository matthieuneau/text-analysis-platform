# app.py - Updated version
import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.gateway.routes import router
from services.gateway.settings import settings
from services.gateway.utils import (
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


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
