from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException, status

from src.api.router import api_router
from src.config import get_settings
from src.inngest import register_inngest

settings = get_settings()

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profile_session_sample_rate=settings.sentry_profiles_sample_rate,
        profile_lifecycle="trace",
        environment=settings.environment,
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Schema changes go through Alembic only — do not call create_all here.
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/sentry-debug")
async def trigger_error() -> dict[str, str]:
    if not settings.allow_sentry_debug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    raise Exception("This is a test error: Sanity test error")


app.include_router(api_router)
register_inngest(app)
