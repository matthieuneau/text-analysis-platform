import uvicorn
from fastapi import FastAPI
from logger import configure_logging, get_logger
from routes import router

configure_logging()

logger = get_logger(__name__)

app = FastAPI(
    title="Text Preprocessing Service",
    description="Microservice for text cleaning, tokenization, and normalization",
    version="1.0.0",
)

app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
