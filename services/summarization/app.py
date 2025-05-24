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
    logger.info("Starting text summarization service...")
    success = load_model()
    if not success:
        logger.error("Failed to load model during startup")
        raise RuntimeError("Failed to load summarization model")
    else:
        logger.info("Service startup completed successfully")

    yield

    # Shutdown (cleanup if needed)
    logger.info("Shutting down text summarization service...")
    # Add any cleanup code here if needed


app = FastAPI(
    title="Text Summarization Service",
    lifespan=lifespan,
    description="Microservice for text summarization using pre-trained models",
    version="1.0.0",
)

# Global variables for model
summarization_pipeline = None
# model_name = "facebook/bart-large-cnn"    # About 1.6GB
model_name = "sshleifer/distilbart-cnn-12-6"  # About 300MB


# Request/Response Models
class TextInput(BaseModel):
    text: str = Field(
        ..., min_length=50, max_length=10000, description="Text to summarize"
    )
    summary_min_length: int = Field(
        default=30, ge=10, le=200, description="Minimum length of summary"
    )
    summary_max_length: int = Field(
        default=150, ge=30, le=500, description="Maximum length of summary"
    )


class SummaryResponse(BaseModel):
    original_text: str
    original_length: int
    summary: str
    summary_length: int
    compression_ratio: float


class KeywordsResponse(BaseModel):
    original_text: str
    keywords: List[str]
    total_keywords: int


# Model initialization
def load_model():
    """Load the summarization model"""
    global summarization_pipeline
    try:
        logger.info(f"Loading summarization model: {model_name}")

        # Load model with explicit device mapping
        device = 0 if torch.cuda.is_available() else -1

        summarization_pipeline = pipeline(
            "summarization",
            model=model_name,
            tokenizer=model_name,
            device=device,
        )

        logger.info("Summarization model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load summarization model: {str(e)}")
        return False


# Health check endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "text-summarization"}


@app.get("/ready")
async def readiness_check():
    """Check if the service is ready to serve requests"""
    if summarization_pipeline is None:
        return {
            "status": "not ready",
            "service": "text-summarization",
            "reason": "model not loaded",
        }
    return {"status": "ready", "service": "text-summarization"}


# Core summarization functions
def summarize_text(
    text: str, max_length: int = 150, min_length: int = 30
) -> Dict[str, Any]:
    """Summarize a single text"""
    if summarization_pipeline is None:
        raise RuntimeError("Summarization model not loaded")

    try:
        # Validate length constraints
        if min_length >= max_length:
            raise ValueError("min_length must be less than max_length")

        # Get summarization from the model
        result = summarization_pipeline(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False,
            truncation=True,
        )

        logger.info(f"Summarization completed for text of length {len(text)}")

        summary_text = result[0]["summary_text"]
        original_length = len(text.split())
        summary_length = len(summary_text.split())
        compression_ratio = (
            round(summary_length / original_length, 3) if original_length > 0 else 0
        )

        return {
            "summary": summary_text,
            "original_length": original_length,
            "summary_length": summary_length,
            "compression_ratio": compression_ratio,
        }

    except Exception as e:
        logger.error(f"Error summarizing text: {str(e)}")
        raise


def extract_keywords(text: str, num_keywords: int = 10) -> List[str]:
    """Extract keywords from text using simple frequency analysis"""
    try:
        # Simple keyword extraction (can be improved with proper NLP libraries)
        import re
        from collections import Counter

        # Remove punctuation and convert to lowercase
        clean_text = re.sub(r"[^\w\s]", "", text.lower())
        words = clean_text.split()

        # Filter out common stop words (basic set)
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
        }

        # Filter words and get frequency
        filtered_words = [
            word for word in words if word not in stop_words and len(word) > 3
        ]
        word_freq = Counter(filtered_words)

        # Get top keywords
        keywords = [word for word, _ in word_freq.most_common(num_keywords)]

        return keywords

    except Exception as e:
        logger.error(f"Error extracting keywords: {str(e)}")
        raise


# API Endpoints
@app.post("/summarize", response_model=SummaryResponse)
async def summarize_text_endpoint(request: TextInput):
    """Summarize a single text"""
    try:
        result = summarize_text(
            request.text,
            max_length=request.summary_max_length,
            min_length=request.summary_min_length,
        )

        return SummaryResponse(
            original_text=request.text,
            summary=result["summary"],
            original_length=result["original_length"],
            summary_length=result["summary_length"],
            compression_ratio=result["compression_ratio"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Text summarization failed: {str(e)}"
        )


class KeywordInput(BaseModel):
    text: str = Field(
        ...,
        min_length=50,
        max_length=10000,
        description="Text to extract keywords from",
    )
    num_keywords: int = Field(
        default=10, ge=1, le=50, description="Number of keywords to extract"
    )


@app.post("/extract-keywords", response_model=KeywordsResponse)
async def extract_keywords_endpoint(request: KeywordInput):
    """Extract keywords from text"""
    try:
        keywords = extract_keywords(request.text, request.num_keywords)

        return KeywordsResponse(
            original_text=request.text,
            keywords=keywords,
            total_keywords=len(keywords),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Keyword extraction failed: {str(e)}"
        )


@app.get("/model-info")
async def get_model_info():
    """Get information about the loaded model"""
    return {
        "model_name": model_name,
        "model_loaded": summarization_pipeline is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "supported_tasks": ["summarization", "keyword_extraction"],
        "max_input_length": 1024,  # BART's typical max length
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)
