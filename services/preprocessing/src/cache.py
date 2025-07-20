import hashlib
import json
import os
import pickle
from typing import Any, Dict, Optional

import redis
from cachetools import LRUCache
from logger import get_logger

logger = get_logger(__name__)

def is_caching_enabled() -> bool:
    """Check if caching is enabled at runtime"""
    return os.getenv("ENABLE_CACHING", "true").lower() == "true"

# LRU caches for each endpoint
clean_cache: LRUCache = LRUCache(maxsize=200)
tokenize_cache: LRUCache = LRUCache(maxsize=200)
normalize_cache: LRUCache = LRUCache(maxsize=200)

# Redis connection (L2 cache)
redis_client: Optional[redis.Redis] = None

if is_caching_enabled():
    try:
        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            decode_responses=False,  # We'll handle pickle serialization
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # Test connection
        redis_client.ping()
        logger.info("Redis L2 cache connected successfully")
    except Exception as e:
        logger.warning(f"Redis L2 cache unavailable: {e}")
        redis_client = None
else:
    logger.info("Caching disabled via ENABLE_CACHING flag")

# Manual hit/miss counters
cache_stats = {
    "clean": {"l1_hits": 0, "l2_hits": 0, "misses": 0},
    "tokenize": {"l1_hits": 0, "l2_hits": 0, "misses": 0},
    "normalize": {"l1_hits": 0, "l2_hits": 0, "misses": 0},
}


def create_cache_key(text: str, options: dict) -> str:
    """Create a consistent cache key from text and options"""
    options_str = json.dumps(options, sort_keys=True)
    combined = f"{text}|{options_str}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def create_redis_key(cache_name: str, cache_key: str) -> str:
    """Create Redis key with service prefix"""
    return f"preprocess:{cache_name}:{cache_key}"


def get_from_redis(cache_name: str, cache_key: str) -> Optional[Any]:
    """Get value from Redis L2 cache"""
    if not redis_client:
        return None

    try:
        redis_key = create_redis_key(cache_name, cache_key)
        data = redis_client.get(redis_key)
        if data:
            return pickle.loads(data)
        return None
    except Exception as e:
        logger.warning(f"Redis get failed: {e}")
        return None


def set_to_redis(cache_name: str, cache_key: str, value: Any, ttl: int = 3600) -> None:
    """Set value to Redis L2 cache with TTL"""
    if not redis_client:
        return

    try:
        redis_key = create_redis_key(cache_name, cache_key)
        serialized = pickle.dumps(value)
        redis_client.setex(redis_key, ttl, serialized)
    except Exception as e:
        logger.warning(f"Redis set failed: {e}")


def cache_with_logging(cache_name: str, cache_obj: LRUCache):
    """Decorator factory that adds two-tier caching with hit/miss logging
    L1 cache is an in-memory LRU cache
    L2 cache is a Redis cache
    """

    def decorator(func):
        def wrapper(text: str, options: dict = {}):
            # Check if caching is enabled at runtime
            if not is_caching_enabled():
                return func(text, options)
                
            cache_key = create_cache_key(text, options)

            # L1 Cache Check (In-Memory LRU)
            if cache_key in cache_obj:
                cache_stats[cache_name]["l1_hits"] += 1
                logger.debug(f"L1 Cache HIT for {func.__name__}", cache_key=cache_key)
                return cache_obj[cache_key]

            # L2 Cache Check (Redis)
            redis_result = get_from_redis(cache_name, cache_key)
            if redis_result is not None:
                cache_stats[cache_name]["l2_hits"] += 1
                logger.debug(f"L2 Cache HIT for {func.__name__}", cache_key=cache_key)
                # Store in L1 for next time
                cache_obj[cache_key] = redis_result
                return redis_result

            # Cache MISS - Execute function
            cache_stats[cache_name]["misses"] += 1
            logger.debug(f"Cache MISS for {func.__name__}", cache_key=cache_key)

            result = func(text, options)

            # Store in both L1 and L2
            cache_obj[cache_key] = result
            set_to_redis(cache_name, cache_key, result)

            logger.debug(
                f"Function {func.__name__} completed and cached",
                cache_key=cache_key,
                l1_cache_size=len(cache_obj),
            )
            return result

        return wrapper

    return decorator


def conditional_cache(cache_name: str, cache_obj: LRUCache):
    """Decorator that conditionally applies caching based on ENABLE_CACHING flag"""
    return cache_with_logging(cache_name, cache_obj)


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about cache usage"""
    return {
        "clean_cache": {
            "l1_size": len(clean_cache),
            "l1_maxsize": clean_cache.maxsize,
            "l1_hits": cache_stats["clean"]["l1_hits"],
            "l2_hits": cache_stats["clean"]["l2_hits"],
            "misses": cache_stats["clean"]["misses"],
        },
        "tokenize_cache": {
            "l1_size": len(tokenize_cache),
            "l1_maxsize": tokenize_cache.maxsize,
            "l1_hits": cache_stats["tokenize"]["l1_hits"],
            "l2_hits": cache_stats["tokenize"]["l2_hits"],
            "misses": cache_stats["tokenize"]["misses"],
        },
        "normalize_cache": {
            "l1_size": len(normalize_cache),
            "l1_maxsize": normalize_cache.maxsize,
            "l1_hits": cache_stats["normalize"]["l1_hits"],
            "l2_hits": cache_stats["normalize"]["l2_hits"],
            "misses": cache_stats["normalize"]["misses"],
        },
        "redis_connected": redis_client is not None,
        "caching_enabled": is_caching_enabled(),
    }
