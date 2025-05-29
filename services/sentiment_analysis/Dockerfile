FROM python:3.13-slim
WORKDIR /app

COPY uv.lock pyproject.toml ./
RUN pip install uv && uv sync --frozen

COPY services/sentiment_analysis .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]