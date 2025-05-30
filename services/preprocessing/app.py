import re
import string
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Text Preprocessing Service",
    description="Microservice for text cleaning, tokenization, and normalization",
    version="1.0.0",
)


# Request/Response Models
class TextInput(BaseModel):
    text: str = Field(
        ..., min_length=1, max_length=10000, description="Text to preprocess"
    )
    options: dict = Field(default_factory=dict, description="Preprocessing options")


class CleanedTextResponse(BaseModel):
    original_text: str
    cleaned_text: str
    operations_applied: List[str]


# TODO: change to List[int] ??
class TokenizedTextResponse(BaseModel):
    original_text: str
    tokens: List[str]
    token_count: int


class NormalizedTextResponse(BaseModel):
    original_text: str
    normalized_text: str
    operations_applied: List[str]


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "preprocessing"}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "preprocessing"}


# Core preprocessing functions
def clean_text(text: str, options: dict = {}) -> tuple[str, List[str]]:
    """Clean text by removing unwanted characters and formatting"""
    operations = []
    cleaned = text

    # Remove extra whitespace
    if options.get("remove_extra_whitespace", True):
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        operations.append("removed_extra_whitespace")

    # Remove URLs
    if options.get("remove_urls", True):
        cleaned = re.sub(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            "",
            cleaned,
        )
        operations.append("removed_urls")

    # Remove email addresses
    if options.get("remove_emails", True):
        cleaned = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "", cleaned
        )
        operations.append("removed_emails")

    # Remove special characters (keep basic punctuation)
    if options.get("remove_special_chars", False):
        cleaned = re.sub(r"[^a-zA-Z0-9\s.,!?;:]", "", cleaned)
        operations.append("removed_special_characters")

    # Remove numbers
    if options.get("remove_numbers", False):
        cleaned = re.sub(r"\d+", "", cleaned)
        operations.append("removed_numbers")

    return cleaned.strip(), operations


# TODO: Add a proper tokenizer?
def tokenize_text(text: str, options: dict = {}) -> List[str]:
    """Simple tokenization - split by whitespace and punctuation"""
    # Basic tokenization
    if options.get("split_punctuation", True):
        # Split on whitespace and separate punctuation
        tokens = re.findall(r"\b\w+\b|[.,!?;]", text.lower())
    else:
        tokens = text.lower().split()

    # Remove empty tokens
    tokens = [token for token in tokens if token.strip()]

    return tokens


def normalize_text(text: str, options: dict = {}) -> tuple[str, List[str]]:
    """Normalize text case and format"""
    operations = []
    normalized = text

    # Convert to lowercase
    if options.get("lowercase", True):
        normalized = normalized.lower()
        operations.append("converted_to_lowercase")

    # Remove punctuation
    if options.get("remove_punctuation", False):
        normalized = normalized.translate(str.maketrans("", "", string.punctuation))
        operations.append("removed_punctuation")

    # Standardize whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    operations.append("standardized_whitespace")

    return normalized, operations


# API Endpoints
@app.post("/clean", response_model=CleanedTextResponse)
async def clean_text_endpoint(request: TextInput):
    """Clean text by removing unwanted elements"""
    try:
        cleaned_text, operations = clean_text(request.text, request.options)
        return CleanedTextResponse(
            original_text=request.text,
            cleaned_text=cleaned_text,
            operations_applied=operations,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text cleaning failed: {str(e)}")


@app.post("/tokenize", response_model=TokenizedTextResponse)
async def tokenize_text_endpoint(request: TextInput):
    """Tokenize text into individual words/tokens"""
    try:
        tokens = tokenize_text(request.text, request.options)
        return TokenizedTextResponse(
            original_text=request.text, tokens=tokens, token_count=len(tokens)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Text tokenization failed: {str(e)}"
        )


@app.post("/normalize", response_model=NormalizedTextResponse)
async def normalize_text_endpoint(request: TextInput):
    """Normalize text format and case"""
    try:
        normalized_text, operations = normalize_text(request.text, request.options)
        return NormalizedTextResponse(
            original_text=request.text,
            normalized_text=normalized_text,
            operations_applied=operations,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Text normalization failed: {str(e)}"
        )


@app.post("/full-preprocess")
async def full_preprocess_endpoint(request: TextInput):
    """Apply all preprocessing steps in sequence"""
    try:
        # Step 1: Clean
        cleaned_text, clean_ops = clean_text(request.text, request.options)

        # Step 2: Normalize
        normalized_text, norm_ops = normalize_text(cleaned_text, request.options)

        # Step 3: Tokenize
        tokens = tokenize_text(normalized_text, request.options)

        return {
            "original_text": request.text,
            "cleaned_text": cleaned_text,
            "normalized_text": normalized_text,
            "tokens": tokens,
            "token_count": len(tokens),
            "operations_applied": clean_ops + norm_ops + ["tokenized"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Full preprocessing failed: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
