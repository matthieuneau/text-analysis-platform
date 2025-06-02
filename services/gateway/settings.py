import os

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class ServiceConfig(BaseModel):
    """Configuration for a single service"""

    url: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 1.0


class Settings(BaseSettings):
    """Application settings"""

    # Gateway configuration
    app_name: str = "Text Analysis Gateway"
    version: str = "1.0.0"
    debug: bool = True

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Logging configuration
    log_level: str = "DEBUG"
    log_format: str = "json"  # json or text

    # Service configurations
    preprocessing_service: ServiceConfig = ServiceConfig(
        url=os.getenv("PREPROCESSING_SERVICE_URL", "http://localhost:8001"),
        timeout=10.0,
        max_retries=3,
        retry_backoff=1.0,
    )

    sentiment_service: ServiceConfig = ServiceConfig(
        url=os.getenv("SENTIMENT_SERVICE_URL", "http://localhost:8002"),
        timeout=30.0,  # Model inference can be slower
        max_retries=3,
        retry_backoff=1.0,
    )

    summarization_service: ServiceConfig = ServiceConfig(
        url=os.getenv("SUMMARIZATION_SERVICE_URL", "http://localhost:8003"),
        timeout=60.0,  # Summarization can be slower
        max_retries=3,
        retry_backoff=2.0,
    )

    # HTTP client configuration
    connection_pool_size: int = 100
    connection_timeout: float = 5.0
    read_timeout: float = 30.0

    # Health check configuration
    health_check_interval: float = 30.0
    health_check_timeout: float = 5.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
