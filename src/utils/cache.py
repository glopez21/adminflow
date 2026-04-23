"""Redis caching service."""

import json
import logging
from typing import Any, Optional

import redis

from config.settings import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service."""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache service."""
        self.redis_url = redis_url or settings.redis_url
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            self.enabled = True
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.client = None
            self.enabled = False

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL in seconds."""
        if not self.enabled:
            return False
        try:
            self.client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.enabled:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.enabled:
            return 0
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
        return 0


cache_service = CacheService()
