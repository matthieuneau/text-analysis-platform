from typing import Dict, List

from pydantic import BaseModel, Field


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


class SentimentResponse(BaseModel):
    original_text: str
    sentiment: str
    confidence: float
    scores: Dict[str, float]


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
