import asyncio
import time
from typing import AsyncGenerator

import torch
from transformers.pipelines import pipeline

from services.summarization.app import logger
from services.summarization.models import StreamEvent


class Summarizer:
    """Handles both streaming and non-streaming summarization"""

    def __init__(self, model_name: str = "Falconsai/text_summarization"):
        self.model_name = model_name
        try:
            # Use a smaller model for faster inference in development
            self.summarizer = pipeline(
                "summarization",
                model=self.model_name,
                device=0 if torch.cuda.is_available() else -1,  # Use GPU if available
            )
            logger.info("Summarization model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError("Model initialization failed")

    async def generate_summary_streaming(
        self, text: str, max_length: int = 130, min_length: int = 30
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Generate summary with streaming events

        Best Practices Demonstrated:
        1. Async generator for memory efficiency
        2. Proper error handling with try/except
        3. Structured event objects
        4. Progress tracking
        5. Non-blocking execution with thread pool
        """
        try:
            # Send start event
            yield StreamEvent(type="start", content="Starting summarization...")

            # Estimate total work for progress tracking
            estimated_tokens = len(text.split()) // 4  # Rough estimate

            # Run CPU-intensive work in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()

            # Simulate progressive generation (in real implementation, you'd use model streaming)
            start_time = time.time()

            # Generate summary (blocking operation moved to thread)
            summary = await loop.run_in_executor(
                None, self._generate_summary_sync, text, max_length, min_length
            )

            # Simulate streaming by yielding tokens progressively
            words = summary.split()
            total_words = len(words)

            current_summary = ""
            for i, word in enumerate(words):
                current_summary += word + " "
                progress = ((i + 1) / total_words) * 100

                yield StreamEvent(type="token", content=word, progress=progress)

                # Small delay to simulate real streaming
                await asyncio.sleep(0.05)

            # Send completion event
            processing_time = time.time() - start_time
            yield StreamEvent(
                type="complete",
                content=f"Summary completed in {processing_time:.2f} seconds",
            )

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield StreamEvent(type="error", content=f"Summarization failed: {str(e)}")

    def _generate_summary_sync(
        self, text: str, max_length: int, min_length: int
    ) -> str:
        """Synchronous summary generation for thread pool execution"""
        try:
            result = self.summarizer(
                text, max_length=max_length, min_length=min_length, do_sample=False
            )
            return result[0]["summary_text"]
        except Exception as e:
            logger.error(f"Model inference error: {e}")
            raise

    async def generate_summary_regular(
        self, text: str, max_length: int = 130, min_length: int = 30
    ) -> tuple[str, float]:
        """Non-streaming summary generation"""
        start_time = time.time()

        # Use thread pool for CPU-intensive work
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(
            None, self._generate_summary_sync, text, max_length, min_length
        )

        processing_time = time.time() - start_time
        return summary, processing_time
