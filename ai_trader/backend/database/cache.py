from __future__ import annotations

import json
import time
from typing import Any, Optional

from backend.config.settings import settings


class Cache:
    """Redis cache with an in-memory fallback when Redis is unavailable."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl: int = 60,
        prefix: str = "ai_trader",
        force_memory: bool = False,
    ) -> None:
        self.ttl = ttl
        self.prefix = prefix
        self._memory: dict[str, tuple[float, str]] = {}
        self._redis = None
        if force_memory:
            return
        url = settings.REDIS_URL if redis_url is None else redis_url
        if not url:
            return
        try:
            import redis

            client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
            client.ping()
            self._redis = client
        except Exception:
            self._redis = None

    @property
    def backend(self) -> str:
        return "redis" if self._redis is not None else "memory"

    def get(self, key: str) -> Optional[Any]:
        namespaced = self._key(key)
        if self._redis is not None:
            raw = self._redis.get(namespaced)
            return None if raw is None else json.loads(raw)
        item = self._memory.get(namespaced)
        if item is None:
            return None
        expires_at, raw = item
        if expires_at < time.monotonic():
            del self._memory[namespaced]
            return None
        return json.loads(raw)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        namespaced = self._key(key)
        raw = json.dumps(value, default=str)
        seconds = self.ttl if ttl is None else ttl
        if self._redis is not None:
            self._redis.set(namespaced, raw, ex=seconds)
            return
        self._memory[namespaced] = (time.monotonic() + seconds, raw)

    def delete(self, key: str) -> None:
        namespaced = self._key(key)
        if self._redis is not None:
            self._redis.delete(namespaced)
            return
        self._memory.pop(namespaced, None)

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"
