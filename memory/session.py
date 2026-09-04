"""
Session state management.

Stores per-call session data in Redis.
Falls back to in-memory storage if Redis is unavailable.

Usage:
    session = SessionManager(call_id="call_123")
    await session.set("customer_name", "John")
    name = await session.get("customer_name")
"""


import json
import os

from typing import Optional, Any

from utils.logging import get_logger

logger=get_logger(__name__)


class SessionManager:
    """
    Manages session state for a single call.

    Tries Redis first, falls back to in-memory.
    """

    def __init__(self, call_id: str, redis_url: Optional[str] = None):
        self.call_id=call_id
        self._key_prefix=f"session:{call_id}"
        self._redis=None
        self._local_store: dict = {}
        self._use_redis=False

        # Try to connect to Redis
        try:
            import redis
            redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
            self._use_redis = True
            logger.info("session_redis_connected", call_id=call_id)
        except Exception as e:
            logger.warning("session_redis_unavailable", call_id=call_id, error=str(e))
            self._use_redis = False


    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the session."""
        full_key = f"{self._key_prefix}:{key}"

        if self._use_redis and self._redis:
            try:
                value = self._redis.get(full_key)
                if value:
                    return json.loads(value)
                return default
            except Exception as e:
                logger.warning("session_redis_get_error", key=key, error=str(e))
                return self._local_store.get(key, default)
        else:
            return self._local_store.get(key, default)


    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set a value in the session."""
        full_key = f"{self._key_prefix}:{key}"

        if self._use_redis and self._redis:
            try:
                self._redis.setex(full_key, ttl, json.dumps(value))
            except Exception as e:
                logger.warning("session_redis_set_error", key=key, error=str(e))
                self._local_store[key] = value
        else:
            self._local_store[key] = value

    async def delete(self, key: str):
        """Delete a value from the session."""
        full_key = f"{self._key_prefix}:{key}"

        if self._use_redis and self._redis:
            try:
                self._redis.delete(full_key)
            except Exception:
                pass

        self._local_store.pop(key, None)


    async def get_all(self) -> dict:
        """Get all session data."""
        if self._use_redis and self._redis:
            try:
                keys = self._redis.keys(f"{self._key_prefix}:*")
                result = {}
                for key in keys:
                    short_key = key.replace(f"{self._key_prefix}:", "")
                    value = self._redis.get(key)
                    if value:
                        result[short_key] = json.loads(value)
                return result
            except Exception:
                return self._local_store.copy()
        else:
            return self._local_store.copy()


    async def clear(self):
        """Clear all session data."""
        if self._use_redis and self._redis:
            try:
                keys = self._redis.keys(f"{self._key_prefix}:*")
                if keys:
                    self._redis.delete(*keys)
            except Exception:
                pass

        self._local_store.clear()