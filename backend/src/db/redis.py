"""Redis cache factory — fail-open NullCache when REDIS_URL unset."""

from functools import lru_cache

from src.config import Settings, get_settings
from src.providers.cache import NullCache, RedisCache
from src.providers.protocols import Cache


@lru_cache
def get_cache() -> Cache:
    settings = get_settings()
    return cache_from_settings(settings)


def cache_from_settings(settings: Settings) -> Cache:
    if settings.environment == "test" or not settings.redis_url:
        return NullCache()
    try:
        return RedisCache(settings)
    except Exception:
        return NullCache()


def clear_cache_singleton() -> None:
    get_cache.cache_clear()
