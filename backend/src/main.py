import sentry_sdk
from fastapi import FastAPI


from src.db import engine
from src.config import get_settings
from src.api.router import api_router

from contextlib import asynccontextmanager


settings = get_settings()

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profile_session_sample_rate=settings.sentry_profiles_sample_rate,
        profile_lifecycle="trace",
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ponytail: create_all only; switch to Alembic when schema evolves
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(title=settings.app_name)


@app.get("/sentry-debug")
async def trigger_error() -> dict[str, str]:
    raise Exception("This is a test error: Sanity test error")


app.include_router(api_router)