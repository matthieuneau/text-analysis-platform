from typing import List

from pydantic import BaseModel, Field


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


# TODO: delete, replaced by SummarizeRequest ??
# # Request/Response Models
# class TextInput(BaseModel):
#     text: str = Field(
#         ..., min_length=50, max_length=10000, description="Text to summarize"
#     )
#     summary_min_length: int = Field(
#         default=30, ge=10, le=200, description="Minimum length of summary"
#     )
#     summary_max_length: int = Field(
#         default=150, ge=30, le=500, description="Maximum length of summary"
#     )


class StreamEvent(BaseModel):
    """Structure for SSE events"""

    type: str  # 'start', 'token', 'progress', 'complete', 'error'
    content: Optional[str] = None
    progress: Optional[float] = None
    timestamp: float = Field(default_factory=time.time)


class SummarizeRequest(BaseModel):
    text: str = Field(
        ..., min_length=10, max_length=10000, description="Text to summarize"
    )
    streaming: Optional[bool] = Field(False, description="Enable streaming response")
    max_length: Optional[int] = Field(
        130, ge=50, le=500, description="Maximum summary length"
    )
    min_length: Optional[int] = Field(
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
