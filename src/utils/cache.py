"""Redis caching service."""

import json
import logging

import redis
from redis import Redis

from config.settings import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service."""

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or settings.redis_url
        self.client: Redis | None = None
        self.enabled = False
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            self.enabled = True
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")

    def get(self, key: str):
        if not self.enabled or self.client is None:
            return None
        try:
            value = self.client.get(key)
            if value is not None:
                return json.loads(value)  # type: ignore[arg-type]
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None

    def set(self, key: str, value, ttl: int = 3600) -> bool:
        if not self.enabled or self.client is None:
            return False
        try:
            self.client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        if not self.enabled or self.client is None:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        if not self.enabled or self.client is None:
            return 0
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)  # type: ignore[misc,return-value]
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
        return 0


cache_service = CacheService()
