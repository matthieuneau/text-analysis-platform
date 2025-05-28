from fastapi import APIRouter, HTTPException

from services.gateway.settings import settings
from services.gateway.utils import get_logger, make_service_request
from services.preprocessing.app import (
    CleanedTextResponse,
    NormalizedTextResponse,
    TextInput,
    TokenizedTextResponse,
)

logger = get_logger()
router = APIRouter()


@router.post("/preprocessing/clean", response_model=CleanedTextResponse)
async def clean_text(request: TextInput):
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
async def normalize_text(request: TextInput):
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
async def full_preprocess(request: TextInput):
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
async def tokenize_text(request: TextInput):
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
