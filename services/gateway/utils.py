# utils.py - Updated version
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

import httpx
import structlog
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from settings import settings
from sqlalchemy.orm import Session

from services.auth.crud import get_db, get_user_by_id
from services.auth.models import User
from services.auth.security import verify_jwt_token
from services.auth.utils import security

# Global variables
http_client: httpx.AsyncClient = None  # type: ignore
_logger: structlog.stdlib.BoundLogger = None  # type: ignore


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


def get_logger() -> structlog.stdlib.BoundLogger:
    """Get the logger instance, initializing if necessary"""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global http_client, _logger

    # Setup logging
    _logger = setup_logging()
    _logger.info("Starting Text Analysis Gateway", version=settings.version)

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

    _logger.info("HTTP client initialized")

    # Check service health on startup
    await check_all_services_health()

    _logger.info("Gateway startup completed successfully")

    yield

    # Shutdown
    _logger.info("Shutting down Text Analysis Gateway")
    if http_client:
        await http_client.aclose()
    _logger.info("Gateway shutdown completed")


async def make_service_request(
    service_config,
    endpoint: str,
    method: str = "GET",
    json_data: Dict | None = None,
    params: Dict | None = None,
) -> Dict[str, Any]:
    """Make a request to a service with retry logic"""
    logger = get_logger()
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

    # This should never be reached due to the retry logic, but satisfies type checker
    raise HTTPException(
        status_code=503, detail=f"Service unavailable after all retries: {url}"
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Main authentication dependency: JWT + Database verification
    1. Verify JWT signature and expiration
    2. Lookup user in database to check current status
    3. Return active user or raise 401
    """
    # Step 1: Verify JWT token
    token_data = verify_jwt_token(credentials.credentials)

    # Step 2: Database lookup to get current user state
    user = get_user_by_id(db, token_data.user_id)

    if not user:
        # User was deleted or deactivated since token was issued
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists"
        )

    if user.is_active is False:
        # User was deactivated since token was issued
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is disabled"
        )

    # TODO: Add token blacklist check here later (for immediate token revocation)

    return user
