from typing import List

from app import app, summarizer
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from logger import logger
from models import (
    KeywordInput,
    KeywordsResponse,
    StreamEvent,
    SummarizeRequest,
    SummarizeResponse,
)


@app.post("/summarize")
async def summarize_text(request: SummarizeRequest, http_request: Request):
    """
    Enhanced summarize endpoint supporting both streaming and regular modes

    Best Practices:
    1. Single endpoint handles both modes (DRY principle)
    2. Proper HTTP status codes and headers
    3. Request validation with Pydantic
    4. Comprehensive error handling
    5. Logging for observability
    6. Client disconnection handling for streaming
    """

    # Log request (be careful with sensitive data in production)
    logger.info(
        f"Summarization request: streaming={request.streaming}, text_length={len(request.text)}"
    )

    try:
        if request.streaming:
            # SSE Streaming Response
            async def generate_sse_stream():
                """
                SSE Format Best Practices:
                1. Proper SSE format with 'data:' prefix
                2. Double newline to separate events
                3. JSON encoding for structured data
                4. Client disconnection detection
                """
                try:
                    async for event in summarizer.generate_summary_streaming(
                        request.text,
                        request.max_length or 130,
                        request.min_length or 30,
                    ):
                        # Check if client disconnected
                        if await http_request.is_disconnected():
                            logger.info("Client disconnected, stopping stream")
                            break

                        # Format as SSE event
                        sse_data = f"data: {event.json()}\n\n"
                        yield sse_data

                except Exception as e:
                    # Send error event in SSE format
                    error_event = StreamEvent(type="error", content=str(e))
                    yield f"data: {error_event.json()}\n\n"

            # Return SSE response with proper headers
            return StreamingResponse(
                generate_sse_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )

        else:
            # Regular JSON Response
            summary, processing_time = await summarizer.generate_summary_regular(
                request.text, request.max_length or 130, request.min_length or 30
            )

            response = SummarizeResponse(
                summary=summary,
                processing_time=processing_time,
                token_count=len(summary.split()),
            )

            logger.info(f"Regular summarization completed in {processing_time:.2f}s")
            return response

    except Exception as e:
        logger.error(f"Summarization error: {e}")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


def extract_keywords(text: str, num_keywords: int = 10) -> List[str]:
    """Extract keywords from text using simple frequency analysis"""
    try:
        # Simple keyword extraction (can be improved with proper NLP libraries)
        import re
        from collections import Counter

        # Remove punctuation and convert to lowercase
        clean_text = re.sub(r"[^\w\s]", "", text.lower())
        words = clean_text.split()

        # Filter out common stop words (basic set)
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
        }

        # Filter words and get frequency
        filtered_words = [
            word for word in words if word not in stop_words and len(word) > 3
        ]
        word_freq = Counter(filtered_words)

        # Get top keywords
        keywords = [word for word, _ in word_freq.most_common(num_keywords)]

        return keywords

    except Exception as e:
        logger.error(f"Error extracting keywords: {str(e)}")
        raise


@app.post("/extract-keywords", response_model=KeywordsResponse)
async def extract_keywords_endpoint(request: KeywordInput):
    """Extract keywords from text"""
    try:
        keywords = extract_keywords(request.text, request.num_keywords)

        return KeywordsResponse(
            original_text=request.text,
            keywords=keywords,
            total_keywords=len(keywords),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Keyword extraction failed: {str(e)}"
        )
