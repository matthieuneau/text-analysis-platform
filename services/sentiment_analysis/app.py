import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers.pipelines import pipeline

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
    description="Microservice for sentiment analysis using pre-trained models",
    version="1.0.0",
)

# Global variables for model and tokenizer
sentiment_pipeline = None
model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"


# Request/Response Models
class TextInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyze")
    # options: dict = Field(default_factory=dict, description="Analysis options")


class BatchTextInput(BaseModel):
    texts: List[str] = Field(
        ..., description="List of texts to analyze", min_length=1, max_length=100
    )
    # options: dict = Field(default_factory=dict, description="Analysis options")


class SentimentResponse(BaseModel):
    original_text: str
    sentiment: str
    confidence: float
    scores: Dict[str, float]


class BatchSentimentResponse(BaseModel):
    results: List[SentimentResponse]
    total_processed: int


# Model initialization
def load_model():
    """Load the sentiment analysis model"""
    global sentiment_pipeline
    try:
        logger.info(f"Loading sentiment model: {model_name}")

        # Load model with explicit device mapping
        device = 0 if torch.cuda.is_available() else -1

        sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model=model_name,
            tokenizer=model_name,  # pipeline calls AutoTokenizer internally
            device=device,
            return_all_scores=True,
        )

        logger.info("Sentiment model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load sentiment model: {str(e)}")
        return False


# Health check endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sentiment-analysis"}


@app.get("/ready")
async def readiness_check():
    """Check if the service is ready to serve requests"""
    if sentiment_pipeline is None:
        return {
            "status": "not ready",
            "service": "sentiment-analysis",
            "reason": "model not loaded",
        }
    return {"status": "ready", "service": "sentiment-analysis"}


# Core sentiment analysis functions
def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Analyze sentiment of a single text"""
    if sentiment_pipeline is None:
        raise RuntimeError("Sentiment model not loaded")

    try:
        # Get predictions from the model
        results = sentiment_pipeline(text)
        logger.info(f"=============Sentiment analysis results: {results}")

        # Process results (model returns all scores)
        scores = {result["label"].lower(): result["score"] for result in results[0]}

        # Map labels to standard sentiment names
        label_mapping = {
            "label_0": "negative",
            "label_1": "neutral",
            "label_2": "positive",
        }

        # Convert labels if needed
        mapped_scores = {}
        for label, score in scores.items():
            mapped_label = label_mapping.get(label, label)
            mapped_scores[mapped_label] = score

        # Find the sentiment with highest confidence
        best_sentiment = max(mapped_scores.items(), key=lambda x: x[1])

        return {
            "sentiment": best_sentiment[0],
            "confidence": best_sentiment[1],
            "scores": mapped_scores,
        }

    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise


# # TODO: Improve efficiency for batch processing (if possible)
# def analyze_batch_sentiment(
#     texts: List[str], options: dict = {}
# ) -> List[Dict[str, Any]]:
#     """Analyze sentiment for multiple texts"""
#     if sentiment_pipeline is None:
#         raise RuntimeError("Sentiment model not loaded")

#     try:
#         # Process in batches for efficiency
#         batch_size = options.get("batch_size", 32)
#         results = []

#         for i in range(0, len(texts), batch_size):
#             batch = texts[i : i + batch_size]
#             batch_results = sentiment_pipeline(batch)

#             for text, result in zip(batch, batch_results):
#                 # Process each result
#                 scores = {r["label"].lower(): r["score"] for r in result}

#                 # Map labels
#                 label_mapping = {
#                     "label_0": "negative",
#                     "label_1": "neutral",
#                     "label_2": "positive",
#                 }

#                 mapped_scores = {}
#                 for label, score in scores.items():
#                     mapped_label = label_mapping.get(label, label)
#                     mapped_scores[mapped_label] = score

#                 best_sentiment = max(mapped_scores.items(), key=lambda x: x[1])

#                 results.append(
#                     {
#                         "text": text,
#                         "sentiment": best_sentiment[0],
#                         "confidence": best_sentiment[1],
#                         "scores": mapped_scores,
#                     }
#                 )

#         return results

#     except Exception as e:
#         logger.error(f"Error in batch sentiment analysis: {str(e)}")
#         raise


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


# @app.post("/batch-analyze", response_model=BatchSentimentResponse)
# async def batch_analyze_sentiment_endpoint(request: BatchTextInput):
#     """Analyze sentiment for multiple texts"""
#     try:
#         results = analyze_batch_sentiment(request.texts, request.options)

#         sentiment_responses = [
#             SentimentResponse(
#                 original_text=result["text"],
#                 sentiment=result["sentiment"],
#                 confidence=result["confidence"],
#                 scores=result["scores"],
#             )
#             for result in results
#         ]

#         return BatchSentimentResponse(
#             results=sentiment_responses, total_processed=len(sentiment_responses)
#         )

#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail=f"Batch sentiment analysis failed: {str(e)}"
#         )


@app.get("/model-info")
async def get_model_info():
    """Get information about the loaded model"""
    return {
        "model_name": model_name,
        "model_loaded": sentiment_pipeline is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "supported_sentiments": ["positive", "negative", "neutral"],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
