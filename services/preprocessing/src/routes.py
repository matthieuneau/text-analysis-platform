import time

from core import clean_text, normalize_text, tokenize_text
from fastapi import APIRouter, HTTPException
from logger import get_logger
from models import (
    CleanedTextResponse,
    NormalizedTextResponse,
    TextInput,
    TokenizedTextResponse,
)

router = APIRouter()

logger = get_logger(__name__)


@router.post("/clean", response_model=CleanedTextResponse)
async def clean_text_endpoint(request: TextInput):
    """Clean text by removing unwanted elements"""
    logger.info("Text cleaning request received", text_length=len(request.text))

    try:
        start_time = time.time()
        cleaned_text, operations = clean_text(request.text, request.options)
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "Text cleaning completed successfully",
            duration_ms=round(duration_ms, 2),
            operations_applied=operations,
        )

        return CleanedTextResponse(
            original_text=request.text,
            cleaned_text=cleaned_text,
            operations_applied=operations,
        )
    except Exception as e:
        logger.error(
            "Text cleaning failed",
            error=str(e),
            error_type=type(e).__name__,
            text_length=len(request.text),
        )
        raise HTTPException(status_code=500, detail=f"Text cleaning failed: {str(e)}")


@router.post("/tokenize", response_model=TokenizedTextResponse)
async def tokenize_text_endpoint(request: TextInput):
    """Tokenize text into individual words/tokens"""
    logger.info("Text tokenization request received", text_length=len(request.text))

    try:
        start_time = time.time()
        tokens = tokenize_text(request.text, request.options)
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "Text tokenization completed successfully",
            duration_ms=round(duration_ms, 2),
            token_count=len(tokens),
        )

        return TokenizedTextResponse(
            original_text=request.text, tokens=tokens, token_count=len(tokens)
        )
    except Exception as e:
        logger.error(
            "Text tokenization failed",
            error=str(e),
            error_type=type(e).__name__,
            text_length=len(request.text),
        )
        raise HTTPException(
            status_code=500, detail=f"Text tokenization failed: {str(e)}"
        )


@router.post("/normalize", response_model=NormalizedTextResponse)
async def normalize_text_endpoint(request: TextInput):
    """Normalize text format and case"""
    logger.info("Text normalization request received", text_length=len(request.text))

    try:
        start_time = time.time()
        normalized_text, operations = normalize_text(request.text, request.options)
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "Text normalization completed successfully",
            duration_ms=round(duration_ms, 2),
            operations_applied=operations,
        )

        return NormalizedTextResponse(
            original_text=request.text,
            normalized_text=normalized_text,
            operations_applied=operations,
        )
    except Exception as e:
        logger.error(
            "Text normalization failed",
            error=str(e),
            error_type=type(e).__name__,
            text_length=len(request.text),
        )
        raise HTTPException(
            status_code=500, detail=f"Text normalization failed: {str(e)}"
        )


@router.post("/full-preprocess")
async def full_preprocess_endpoint(request: TextInput):
    """Apply all preprocessing steps in sequence"""
    logger.info("Full preprocessing request received", text_length=len(request.text))

    try:
        start_time = time.time()

        # Step 1: Clean
        logger.debug("Starting cleaning step")
        cleaned_text, clean_ops = clean_text(request.text, request.options)

        # Step 2: Normalize
        logger.debug("Starting normalization step")
        normalized_text, norm_ops = normalize_text(cleaned_text, request.options)

        # Step 3: Tokenize
        logger.debug("Starting tokenization step")
        tokens = tokenize_text(normalized_text, request.options)

        duration_ms = (time.time() - start_time) * 1000
        all_operations = clean_ops + norm_ops + ["tokenized"]

        logger.info(
            "Full preprocessing completed successfully",
            duration_ms=round(duration_ms, 2),
            final_token_count=len(tokens),
            total_operations=len(all_operations),
        )

        return {
            "original_text": request.text,
            "cleaned_text": cleaned_text,
            "normalized_text": normalized_text,
            "tokens": tokens,
            "token_count": len(tokens),
            "operations_applied": all_operations,
        }
    except Exception as e:
        logger.error(
            "Full preprocessing failed",
            error=str(e),
            error_type=type(e).__name__,
            text_length=len(request.text),
        )
        raise HTTPException(
            status_code=500, detail=f"Full preprocessing failed: {str(e)}"
        )


@router.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "preprocessing"}


# Health check endpoint
@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "preprocessing"}
