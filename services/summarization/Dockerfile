FROM python:3.13-slim
WORKDIR /app

COPY uv.lock pyproject.toml ./
RUN pip install uv && uv sync --frozen

COPY services/summarization .

EXPOSE 8000

CMD ["uv", "run", "app.py"]