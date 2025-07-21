# Base stage - common dependencies
FROM python:3.13-slim AS base
WORKDIR /app
RUN pip install uv

COPY services/preprocessing/uv.lock services/preprocessing/pyproject.toml ./
RUN pip install uv && uv sync
RUN mkdir src

COPY services/preprocessing/src src/
COPY services/preprocessing/gunicorn.conf.py ./

EXPOSE 8000
CMD ["uv", "run", "gunicorn", "-c", "gunicorn.conf.py", "src.app:app"]

# Production stage - minimal and optimized
FROM base AS prod
# Clean up unnecessary packages
RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uv", "run", "gunicorn", "-c", "gunicorn.conf.py", "src.app:app"]
