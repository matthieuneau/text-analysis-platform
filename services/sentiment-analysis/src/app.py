import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

import numpy as np
import onnxruntime as ort
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoTokenizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting sentiment analysis service...")
    success = load_model()
    if not success:
        logger.error("Failed to load model during startup")
        raise RuntimeError("Failed to load sentiment model")
    else:
        logger.info("Service startup completed successfully")

    yield

    # Shutdown (cleanup if needed)
    logger.info("Shutting down sentiment analysis service...")
    # Add any cleanup code here if needed


app = FastAPI(
    title="Sentiment Analysis Service",
    lifespan=lifespan,
    description="Microservice for sentiment analysis using pure ONNX Runtime",
    version="1.0.0",
)

# Global variables for model and tokenizer
ort_session = None  # type: ignore
tokenizer = None  # type: ignore
model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"

onnx_model_path = "/opt/models/model.onnx"


# Request/Response Models
class TextInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyze")


class SentimentResponse(BaseModel):
    original_text: str
    sentiment: str
    confidence: float
    scores: Dict[str, float]


# Model initialization
def load_model() -> bool:
    """Load the ONNX sentiment analysis model"""
    global ort_session, tokenizer
    try:
        # Check if ONNX model exists
        if not os.path.exists(onnx_model_path):
            logger.error(f"ONNX model not found at {onnx_model_path}")

        logger.info(f"Loading ONNX model from: {onnx_model_path}")

        # Create ONNX Runtime session
        ort_session = ort.InferenceSession(onnx_model_path)
        logger.info("ONNX model and tokenizer loaded successfully")

        # Load tokenizer from HuggingFace (this doesn't require PyTorch)
        tokenizer = AutoTokenizer.from_pretrained(model_name)

        logger.info(
            f"Model inputs: {[input.name for input in ort_session.get_inputs()]}"
        )
        logger.info(
            f"Model outputs: {[output.name for output in ort_session.get_outputs()]}"
        )

        return True

    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        return False


# Health check endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sentiment-analysis"}


@app.get("/ready")
async def readiness_check():
    """Check if the service is ready to serve requests"""
    if ort_session is None or tokenizer is None:
        return {
            "status": "not ready",
            "service": "sentiment-analysis",
            "reason": "model not loaded",
        }
    return {"status": "ready", "service": "sentiment-analysis"}


# Core sentiment analysis functions
def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Analyze sentiment using pure ONNX Runtime"""
    if ort_session is None or tokenizer is None:
        raise RuntimeError("Model not loaded")

    try:
        # Use np to avoid PyTorch dependency at runtime
        inputs = tokenizer(
            text, return_tensors="np", truncation=True, max_length=512, padding=True
        )

        # Prepare inputs for ONNX Runtime
        ort_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
        }

        # Run inference
        ort_outputs = ort_session.run(None, ort_inputs)
        logits = ort_outputs[0]  # First output is logits

        # Apply softmax to get probabilities
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probabilities = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)
        scores = probabilities[0].tolist()

        logger.info(f"Sentiment analysis scores: {scores}")

        # Map to sentiment labels (0=negative, 1=neutral, 2=positive)
        sentiment_labels = ["negative", "neutral", "positive"]
        mapped_scores = {sentiment_labels[i]: scores[i] for i in range(len(scores))}

        # Find the sentiment with highest confidence
        best_sentiment_idx = scores.index(max(scores))
        best_sentiment = sentiment_labels[best_sentiment_idx]
        confidence = scores[best_sentiment_idx]

        return {
            "sentiment": best_sentiment,
            "confidence": confidence,
            "scores": mapped_scores,
        }

    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise


# API Endpoints
@app.post("/analyze", response_model=SentimentResponse)
async def analyze_sentiment_endpoint(request: TextInput):
    """Analyze sentiment of a single text"""
    try:
        result = analyze_sentiment(request.text)

        return SentimentResponse(
            original_text=request.text,
            sentiment=result["sentiment"],
            confidence=result["confidence"],
            scores=result["scores"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Sentiment analysis failed: {str(e)}"
        )


@app.get("/model-info")
async def get_model_info():
    """Get information about the loaded model"""
    return {
        "model_name": model_name,
        "model_path": onnx_model_path,
        "model_loaded": ort_session is not None,
        "runtime": "Pure ONNX Runtime",
        "device": "cpu",
        "providers": ort.get_available_providers() if ort_session else [],
        "supported_sentiments": ["positive", "negative", "neutral"],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
