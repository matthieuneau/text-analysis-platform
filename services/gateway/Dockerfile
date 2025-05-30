FROM python:3.13-slim
WORKDIR /app

# Copy requirements and install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen    

# Copy service code
COPY services/gateway .

EXPOSE 8000

CMD ["uv", "run", "app.py"]
