# Request/Response Models
from typing import List

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
