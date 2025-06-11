from contextlib import asynccontextmanager

import torch
import uvicorn
from fastapi import FastAPI
from logger import logger
from summarizer import Summarizer

# Configure logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events
    Replaces the deprecated @app.on_event decorators
    """
    # Startup
    global summarizer
    logger.info("Loading summarization model...")
    try:
        summarizer = Summarizer()
        logger.info("Summarization service ready")
    except Exception as e:
        logger.error(f"Failed to initialize summarizer: {e}")
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("Summarization service shutting down...")
    # Cleanup resources if needed


app = FastAPI(
    title="Text Summarization Service",
    lifespan=lifespan,
    description="Microservice for text summarization using pre-trained models",
    version="1.0.0",
)

# Global summarizer instance (initialized in lifespan)
summarizer: Summarizer = None  # type: ignore


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "text-summarization"}


@app.get("/ready")
async def readiness_check():
    """Check if the service is ready to serve requests"""
    if summarizer is None:
        return {
            "status": "not ready",
            "service": "text-summarization",
            "reason": "model not loaded",
        }
    return {"status": "ready", "service": "text-summarization"}


@app.get("/model-info")
async def get_model_info():
    """Get information about the loaded model"""
    return {
        "model_name": summarizer.model_name,
        "model_loaded": summarizer is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "supported_tasks": ["summarization", "keyword_extraction"],
        "max_input_length": 1024,  # BART's typical max length
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
