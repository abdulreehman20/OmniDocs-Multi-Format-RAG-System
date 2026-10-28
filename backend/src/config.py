from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "backend"
    environment: EnvironmentName = "development"
    debug: bool = False

    # Sentry
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 1.0
    sentry_profiles_sample_rate: float = 1.0

    # Propel Auth (temporary until Phase 1 Neon Managed Better Auth)
    propelauth_auth_url: str
    propelauth_api_key: str

    # Postgres
    database_url: str
    database_url_pooled: str

    # Neon Object Storage (S3-compatible) — real client in Phase 1
    aws_region: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_endpoint_url_s3: str | None = None
    s3_bucket_documents: str = "documents"

    # Redis (Phase 4); optional in Phase 0
    redis_url: str | None = None

    # Inngest
    inngest_app_id: str = "rag-basic"
    inngest_event_key: str | None = None
    inngest_signing_key: str | None = None
    inngest_dev: bool = Field(
        default=True,
        description="Use Inngest Dev Server mode when True",
    )

    # Provider keys reserved for later phases
    pinecone_api_key: str | None = None
    openrouter_api_key: str | None = None

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def allow_sentry_debug(self) -> bool:
        return self.environment in ("development", "test")


@lru_cache
def get_settings() -> Settings:
    return Settings()
