from typing import Dict

from pydantic import BaseModel, Field


class SentimentResponse(BaseModel):
    original_text: str
    sentiment: str
    confidence: float
    scores: Dict[str, float]


# Request/Response Models
class TextInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyze")
