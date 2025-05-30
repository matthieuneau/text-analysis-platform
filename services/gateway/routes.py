from fastapi import APIRouter, HTTPException
from schemas import (
    CleanedTextResponse,
    KeywordInput,
    KeywordsResponse,
    NormalizedTextResponse,
    SentimentResponse,
    SummaryResponse,
    TokenizedTextResponse,
)

# Creating 2 aliases for now, might change later
from schemas import TextInput as PreprocessingTextInput
from schemas import TextInput as SentimentTextInput
from schemas import (
    TextInput as SummarizationTextInput,
)
from settings import settings
from utils import get_logger, make_service_request

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


@router.post("/summarization/summarize", response_model=SummaryResponse)
async def summarize_text(request: SummarizationTextInput):
    """Summarize text via summarization service"""
    try:
        result = await make_service_request(
            settings.summarization_service,
            "summarize",
            "POST",
            json_data=request.model_dump(),
        )
        return SummaryResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to summarize text", error=str(e))
        raise HTTPException(status_code=500, detail="Text summarization failed")


@router.post("/summarization/extract-keywords", response_model=KeywordsResponse)
async def extract_keywords(request: KeywordInput):
    """Extract keywords from text via summarization service"""
    try:
        result = await make_service_request(
            settings.summarization_service,
            "extract-keywords",
            "POST",
            json_data=request.model_dump(),
        )
        return KeywordsResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to extract keywords", error=str(e))
        raise HTTPException(status_code=500, detail="Keyword extraction failed")


@router.get("/summarization/model-info")
async def get_summarization_model_info():
    """Get summarization model information"""
    try:
        result = await make_service_request(
            settings.summarization_service,
            "model-info",
            "GET",
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get summarization model info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get model information")


@router.get("/summarization/ready")
async def check_summarization_readiness():
    """Check if summarization service is ready"""
    try:
        result = await make_service_request(
            settings.summarization_service,
            "ready",
            "GET",
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check summarization service readiness", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to check service readiness")
