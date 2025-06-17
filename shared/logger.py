"""
Comprehensive logging configuration using structlog for microservices.
This module provides consistent, structured logging across all services.
"""

import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, Optional

import structlog
from structlog.types import EventDict, Processor

# Environment configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SERVICE_NAME = os.getenv("SERVICE_NAME", "unknown-service")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "unknown")


def add_service_context(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add service-level context to all log entries"""
    event_dict["service"] = SERVICE_NAME
    event_dict["version"] = SERVICE_VERSION
    event_dict["environment"] = ENVIRONMENT
    return event_dict


def add_correlation_id(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add correlation ID if available in context"""
    # This will be populated by middleware in gateway service
    correlation_id = getattr(structlog.contextvars, "correlation_id", None)
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def add_request_context(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add request context if available (for gateway service)"""
    request_id = getattr(structlog.contextvars, "request_id", None)
    user_id = getattr(structlog.contextvars, "user_id", None)
    endpoint = getattr(structlog.contextvars, "endpoint", None)

    if request_id:
        event_dict["request_id"] = request_id
    if user_id:
        event_dict["user_id"] = user_id
    if endpoint:
        event_dict["endpoint"] = endpoint

    return event_dict


def filter_sensitive_data(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Remove or mask sensitive information from logs"""
    sensitive_keys = {
        "password",
        "token",
        "api_key",
        "secret",
        "auth",
        "authorization",
        "credit_card",
        "ssn",
        "social_security",
        "passport",
    }

    def mask_value(key: str, value: Any) -> Any:
        if isinstance(key, str) and any(
            sensitive in key.lower() for sensitive in sensitive_keys
        ):
            return "[REDACTED]"
        return value

    # Recursively mask sensitive data
    def mask_dict(d: EventDict) -> EventDict:
        return {
            k: mask_value(k, mask_dict(v) if isinstance(v, dict) else v)
            for k, v in d.items()
        }

    return mask_dict(event_dict)


# def performance_processor(
#     logger: Any, method_name: str, event_dict: EventDict
# ) -> EventDict:
#     """Add performance-related metadata"""
#     # Can be extended to add memory usage, CPU time, etc.
#     if "duration_ms" in event_dict:
#         # Add performance categorization
#         duration = event_dict["duration_ms"]
#         if duration > 5000:
#             event_dict["performance_category"] = "slow"
#         elif duration > 1000:
#             event_dict["performance_category"] = "medium"
#         else:
#             event_dict["performance_category"] = "fast"
# return event_dict


# def error_processor(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
#     """Enhanced error processing"""
#     if "error" in event_dict or "exception" in event_dict:
#         event_dict["event_type"] = "error"

#         # Add error categorization
#         error_msg = str(event_dict.get("error", event_dict.get("exception", "")))
#         if "timeout" in error_msg.lower():
#             event_dict["error_category"] = "timeout"
#         elif "connection" in error_msg.lower():
#             event_dict["error_category"] = "network"
#         elif "permission" in error_msg.lower() or "auth" in error_msg.lower():
#             event_dict["error_category"] = "authorization"
#         else:
#             event_dict["error_category"] = "unknown"

#     return event_dict


# Development-friendly console renderer
def dev_console_renderer(logger: Any, method_name: str, event_dict: EventDict) -> str:
    """Pretty console output for development"""
    # timestamp = event_dict.pop("timestamp", "")
    level = event_dict.pop("level", "INFO")
    service = event_dict.pop("service", "")
    event = event_dict.pop("event", "")

    # Format main message
    main_msg = f"[{level}] {service}: {event}"

    # Add context if available
    context_parts = []
    for key, value in event_dict.items():
        if key not in ["logger", "event_dict"]:
            context_parts.append(f"{key}={value}")

    if context_parts:
        context_str = " | " + ", ".join(context_parts)
        return main_msg + context_str

    return main_msg


# Alternative processors you might want to enable:


def sampling_processor(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Sample logs based on level or criteria"""
    import random

    # Sample debug logs at 10% rate
    if event_dict.get("level") == "debug" and random.random() > 0.1:
        raise structlog.DropEvent

    return event_dict


# def metric_extraction_processor(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
#     """Extract metrics from log events"""
#     # Could send metrics to Prometheus here
#     if "duration_ms" in event_dict:
#         # prometheus_client.histogram.observe(event_dict["duration_ms"])
#         pass
#
#     return event_dict


# def external_system_processor(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
#     """Send certain log events to external systems"""
#     if event_dict.get("level") == "error":
#         # Could send to Sentry, PagerDuty, etc.
#         pass
#
#     return event_dict


def configure_logging():
    """Configure structlog for the service"""

    # Determine output format based on environment
    if ENVIRONMENT == "development":
        # Pretty console output for development
        processors = [
            structlog.contextvars.merge_contextvars,
            add_service_context,
            add_correlation_id,
            add_request_context,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            # filter_sensitive_data,
            # performance_processor,
            # error_processor,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # Use pretty console output in development
            structlog.dev.ConsoleRenderer(colors=True),
            # Uncomment below for JSON even in development:
            # structlog.processors.JSONRenderer(sort_keys=True)
        ]
    else:
        # JSON output for production (Loki-friendly)
        processors = [
            structlog.contextvars.merge_contextvars,
            add_service_context,
            add_correlation_id,
            add_request_context,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            # filter_sensitive_data,
            # performance_processor,
            # error_processor,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # JSON output for production
            structlog.processors.JSONRenderer(sort_keys=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, LOG_LEVEL, logging.INFO),
    )

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # logging.getLogger("httpx").setLevel(logging.WARNING)
    # logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)


# # Context managers for adding context to logs
# class log_context:
#     """Context manager for adding temporary context to logs"""

#     def __init__(self, **kwargs):
#         self.context = kwargs
#         self.tokens = []

#     def __enter__(self):
#         for key, value in self.context.items():
#             token = structlog.contextvars.bind_contextvars(**{key: value})
#             self.tokens.append(token)
#         return self

#     def __exit__(self, exc_type, exc_val, exc_tb):
#         for token in reversed(self.tokens):
#             token.reset()


# # Performance timing decorator
# def log_performance(operation_name: str):
#     """Decorator to automatically log operation performance"""

#     def decorator(func):
#         def wrapper(*args, **kwargs):
#             logger = get_logger()
#             start_time = time.time()

#             try:
#                 logger.info("Operation started", operation=operation_name)
#                 result = func(*args, **kwargs)
#                 duration_ms = (time.time() - start_time) * 1000
#                 logger.info(
#                     "Operation completed",
#                     operation=operation_name,
#                     duration_ms=round(duration_ms, 2),
#                     status="success",
#                 )
#                 return result
#             except Exception as e:
#                 duration_ms = (time.time() - start_time) * 1000
#                 logger.error(
#                     "Operation failed",
#                     operation=operation_name,
#                     duration_ms=round(duration_ms, 2),
#                     error=str(e),
#                     status="error",
#                 )
#                 raise

#         return wrapper

#     return decorator


# Example usage patterns:
"""
# Basic logging
logger = get_logger(__name__)
logger.info("Service started", port=8000)

# With context
with log_context(user_id="123", operation="text_processing"):
    logger.info("Processing started")
    # All logs within this block will include user_id and operation

# Performance logging
@log_performance("text_cleaning")
def clean_text(text):
    # Function implementation
    pass

# Error logging with context
try:
    process_text()
except Exception as e:
    logger.error("Text processing failed", 
                error=str(e), 
                text_length=len(text),
                processing_options=options)
"""
