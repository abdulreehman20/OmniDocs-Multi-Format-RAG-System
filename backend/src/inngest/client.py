from functools import lru_cache

import inngest
from src.config import get_settings


@lru_cache
def get_inngest_client() -> inngest.Inngest:
    settings = get_settings()
    return inngest.Inngest(
        app_id=settings.inngest_app_id,
        is_production=settings.is_production,
        event_key=settings.inngest_event_key,
        signing_key=settings.inngest_signing_key,
    )
