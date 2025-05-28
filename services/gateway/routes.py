from fastapi import APIRouter, HTTPException

from services.gateway.settings import settings
from services.gateway.utils import get_logger, make_service_request
from services.preprocessing.app import (
    CleanedTextResponse,
    NormalizedTextResponse,
    TokenizedTextResponse,
)
from services.preprocessing.app import (
    TextInput as PreprocessingTextInput,
)
from services.sentiment_analysis.app import SentimentResponse
from services.sentiment_analysis.app import TextInput as SentimentTextInput

logger = get_logger()
router = APIRouter()


@router.post("/preprocessing/clean", response_model=CleanedTextResponse)
async def clean_text(request: PreprocessingTextInput):
    """Clean text via preprocessing service"""
    try:
        result = await make_service_request(
            settings.preprocessing_service,
            "clean",
            "POST",
            json_data=request.model_dump(),
        )
        return CleanedTextResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to clean text", error=str(e))
        raise HTTPException(status_code=500, detail="Text cleaning failed")


@router.post("/preprocessing/normalize", response_model=NormalizedTextResponse)
async def normalize_text(request: PreprocessingTextInput):
    """Normalize text via preprocessing service"""
    try:
        result = await make_service_request(
            settings.preprocessing_service,
            "normalize",
            "POST",
            json_data=request.model_dump(),
        )
        return NormalizedTextResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to normalize text", error=str(e))
        raise HTTPException(status_code=500, detail="Text normalization failed")


@router.post("/preprocessing/full-preprocess")
async def full_preprocess(request: PreprocessingTextInput):
    """router all preprocessing steps via preprocessing service"""
    try:
        result = await make_service_request(
            settings.preprocessing_service,
            "full-preprocess",
            "POST",
            json_data=request.model_dump(),
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to preprocess text", error=str(e))
        raise HTTPException(status_code=500, detail="Full preprocessing failed")


@router.post("/preprocessing/tokenize", response_model=TokenizedTextResponse)
async def tokenize_text(request: PreprocessingTextInput):
    """Tokenize text via preprocessing service"""
    try:
        result = await make_service_request(
            settings.preprocessing_service,
            "tokenize",
            "POST",
            json_data=request.model_dump(),
        )
        return TokenizedTextResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to tokenize text", error=str(e))
        raise HTTPException(status_code=500, detail="Text tokenization failed")


@router.post("/sentiment/analyze", response_model=SentimentResponse)
async def analyze_sentiment(request: SentimentTextInput):
    """Analyze sentiment of text via sentiment analysis service"""
    try:
        result = await make_service_request(
            settings.sentiment_service,
            "analyze",
            "POST",
            json_data=request.model_dump(),
        )
        return SentimentResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to analyze sentiment", error=str(e))
        raise HTTPException(status_code=500, detail="Sentiment analysis failed")


@router.get("/sentiment/model-info")
async def get_sentiment_model_info():
    """Get sentiment analysis model information"""
    try:
        result = await make_service_request(
            settings.sentiment_service,
            "model-info",
            "GET",
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get model info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get model information")
