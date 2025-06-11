import time
from typing import List

from pydantic import BaseModel, Field


class SummarizeResponse(BaseModel):
    summary: str
    processing_time: float
    token_count: int


class KeywordsResponse(BaseModel):
    original_text: str
    keywords: List[str]
    total_keywords: int


class StreamEvent(BaseModel):
    """Structure for SSE events"""

    type: str  # 'start', 'token', 'progress', 'complete', 'error'
    content: str | None = None
    progress: float | None = None
    timestamp: float = Field(default_factory=time.time)


class SummarizeRequest(BaseModel):
    text: str = Field(
        ..., min_length=10, max_length=10000, description="Text to summarize"
    )
    streaming: bool | None = Field(False, description="Enable streaming response")
    max_length: int | None = Field(
        130, ge=50, le=500, description="Maximum summary length"
    )
    min_length: int | None = Field(
        30, ge=10, le=100, description="Minimum summary length"
    )

    class Config:
        # Enable validation for assignment
        validate_assignment = True
        # Example for API documentation
        schema_extra = {
            "example": {
                "text": "Your long text to summarize goes here...",
                "streaming": True,
                "max_length": 150,
                "min_length": 50,
            }
        }


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
