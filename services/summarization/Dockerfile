# Base stage - common dependencies
FROM python:3.13-slim AS base
WORKDIR /app

COPY uv.lock pyproject.toml ./
RUN pip install uv && uv sync --frozen

COPY services/summarization .

# Production stage - minimal and optimized
FROM base AS production
# Clean up unnecessary packages
RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uv", "run", "app.py"]

# Development stage - includes dev tools and debugging capabilities
FROM base AS development
# Install development and debugging tools
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    vim \
    htop \
    procps \
    net-tools \
    telnet \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Keep root user for easier debugging
EXPOSE 8000
CMD ["uv", "run", "app.py"]