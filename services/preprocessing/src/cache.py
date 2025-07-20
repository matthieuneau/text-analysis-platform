import hashlib
import json
from typing import Any, Dict, List, Tuple

from cachetools import LRUCache, cached
from logger import get_logger

logger = get_logger(__name__)

# LRU caches for each endpoint
clean_cache: LRUCache = LRUCache(maxsize=200)
tokenize_cache: LRUCache = LRUCache(maxsize=200)
normalize_cache: LRUCache = LRUCache(maxsize=200)

# Manual hit/miss counters since LRUCache doesn't track them
cache_stats = {
    "clean": {"hits": 0, "misses": 0},
    "tokenize": {"hits": 0, "misses": 0},
    "normalize": {"hits": 0, "misses": 0},
}


def create_cache_key(text: str, options: dict) -> str:
    """Create a consistent cache key from text and options"""
    options_str = json.dumps(options, sort_keys=True)
    combined = f"{text}|{options_str}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def cache_with_logging(cache_name: str, cache_obj: LRUCache):
    """Decorator factory that adds caching with hit/miss logging"""

    def decorator(func):
        # Create the cached function first, cannot use the cache decorator, as it would not allow us to log hits/misses (bypass the fct altogether in case of a hit)
        cached_func = cached(
            cache_obj, key=lambda text, options={}: create_cache_key(text, options)
        )(func)

        def wrapper(text: str, options: dict = {}):
            cache_key = create_cache_key(text, options)

            # Check if it's a hit or miss BEFORE calling cached function
            if cache_key in cache_obj:
                cache_stats[cache_name]["hits"] += 1
                logger.debug(f"Cache HIT for {func.__name__}", cache_key=cache_key)
            else:
                cache_stats[cache_name]["misses"] += 1
                logger.debug(f"Cache MISS for {func.__name__}", cache_key=cache_key)

            # Call the cached function
            result = cached_func(text, options)

            logger.debug(
                f"Function {func.__name__} completed",
                cache_key=cache_key,
                cache_size=len(cache_obj),
            )
            return result

        return wrapper

    return decorator


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about cache usage"""
    return {
        "clean_cache": {
            "size": len(clean_cache),
            "maxsize": clean_cache.maxsize,
            "hits": cache_stats["clean"]["hits"],
            "misses": cache_stats["clean"]["misses"],
        },
        "tokenize_cache": {
            "size": len(tokenize_cache),
            "maxsize": tokenize_cache.maxsize,
            "hits": cache_stats["tokenize"]["hits"],
            "misses": cache_stats["tokenize"]["misses"],
        },
        "normalize_cache": {
            "size": len(normalize_cache),
            "maxsize": normalize_cache.maxsize,
            "hits": cache_stats["normalize"]["hits"],
            "misses": cache_stats["normalize"]["misses"],
        },
    }
