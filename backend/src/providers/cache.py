from __future__ import annotations

import json
import logging
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from src.config import Settings

logger = logging.getLogger(__name__)


class NullCache:
    """No-op fail-open cache when Redis is unset."""

    def get_json(self, key: str) -> Any | None:
        _ = key
        return None

    def set_json(self, key: str, value: Any, *, ttl_seconds: int) -> bool:
        _ = key, value, ttl_seconds
        return False

    def delete(self, key: str) -> bool:
        _ = key
        return False


class RedisCache:
    def __init__(self, settings: Settings) -> None:
        if not settings.redis_url:
            raise ValueError("REDIS_URL is required for RedisCache")
        self._max_bytes = settings.cache_max_payload_bytes
        self._client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=settings.redis_connect_timeout_seconds,
            socket_timeout=settings.redis_socket_timeout_seconds,
            decode_responses=True,
        )

    def get_json(self, key: str) -> Any | None:
        try:
            raw = self._client.get(key)
        except RedisError:
            logger.warning("redis get failed key=%s", key[:80], exc_info=True)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: Any, *, ttl_seconds: int) -> bool:
        try:
            payload = json.dumps(value, separators=(",", ":"))
        except (TypeError, ValueError):
            return False
        if len(payload.encode("utf-8")) > self._max_bytes:
            return False
        try:
            self._client.set(key, payload, ex=max(1, ttl_seconds))
            return True
        except RedisError:
            logger.warning("redis set failed key=%s", key[:80], exc_info=True)
            return False

    def delete(self, key: str) -> bool:
        try:
            self._client.delete(key)
            return True
        except RedisError:
            logger.warning("redis delete failed key=%s", key[:80], exc_info=True)
            return False


class FakeCache:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self.fail_open = False

    def get_json(self, key: str) -> Any | None:
        if self.fail_open:
            return None
        return self.store.get(key)

    def set_json(self, key: str, value: Any, *, ttl_seconds: int) -> bool:
        _ = ttl_seconds
        if self.fail_open:
            return False
        self.store[key] = value
        return True

    def delete(self, key: str) -> bool:
        if self.fail_open:
            return False
        self.store.pop(key, None)
        return True
