import re
import string
from typing import List

from logger import get_logger

logger = get_logger(__name__)


def clean_text(text: str, options: dict = {}) -> tuple[str, List[str]]:
    """Clean text by removing unwanted characters and formatting"""
    logger.debug("Starting text cleaning", text_length=len(text), options=options)

    operations = []
    cleaned = text
    original_length = len(text)

    # Remove extra whitespace
    if options.get("remove_extra_whitespace", True):
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        operations.append("removed_extra_whitespace")

    # Remove URLs
    if options.get("remove_urls", True):
        url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        urls_found = len(re.findall(url_pattern, cleaned))
        cleaned = re.sub(url_pattern, "", cleaned)
        operations.append("removed_urls")
        if urls_found > 0:
            logger.debug("URLs removed", url_count=urls_found)

    # Remove email addresses
    if options.get("remove_emails", True):
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails_found = len(re.findall(email_pattern, cleaned))
        cleaned = re.sub(email_pattern, "", cleaned)
        operations.append("removed_emails")
        if emails_found > 0:
            logger.debug("Emails removed", email_count=emails_found)

    # Remove special characters
    if options.get("remove_special_chars", False):
        cleaned = re.sub(r"[^a-zA-Z0-9\s.,!?;:]", "", cleaned)
        operations.append("removed_special_characters")

    # Remove numbers
    if options.get("remove_numbers", False):
        numbers_found = len(re.findall(r"\d+", cleaned))
        cleaned = re.sub(r"\d+", "", cleaned)
        operations.append("removed_numbers")
        if numbers_found > 0:
            logger.debug("Numbers removed", number_count=numbers_found)

    final_length = len(cleaned.strip())
    reduction_percentage = (
        ((original_length - final_length) / original_length * 100)
        if original_length > 0
        else 0
    )

    logger.info(
        "Text cleaning completed",
        original_length=original_length,
        final_length=final_length,
        reduction_percentage=round(reduction_percentage, 2),
        operations=operations,
    )

    return cleaned.strip(), operations


def tokenize_text(text: str, options: dict = {}) -> List[str]:
    """Simple tokenization - split by whitespace and punctuation"""
    logger.debug("Starting tokenization", text_length=len(text))

    # Basic tokenization
    if options.get("split_punctuation", True):
        tokens = re.findall(r"\b\w+\b|[.,!?;]", text.lower())
    else:
        tokens = text.lower().split()

    # Remove empty tokens
    tokens = [token for token in tokens if token.strip()]

    logger.info(
        "Tokenization completed",
        token_count=len(tokens),
        average_token_length=round(sum(len(t) for t in tokens) / len(tokens), 2)
        if tokens
        else 0,
    )

    return tokens


def normalize_text(text: str, options: dict = {}) -> tuple[str, List[str]]:
    """Normalize text case and format"""
    logger.debug("Starting normalization", text_length=len(text))

    operations = []
    normalized = text
    original_length = len(text)

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

    logger.info(
        "Normalization completed",
        original_length=original_length,
        final_length=len(normalized),
        operations=operations,
    )

    return normalized, operations
