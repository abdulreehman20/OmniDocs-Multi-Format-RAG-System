from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
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

    # Neon Managed Better Auth (JWT issuer / JWKS)
    neon_auth_base_url: str = "https://auth.example.neon.tech/neondb/auth"
    neon_auth_jwks_url: str | None = None
    # HS256 secret for ENVIRONMENT=test only (never use in production)
    jwt_test_secret: str | None = "test-jwt-secret-do-not-use-in-prod-32b"

    # Postgres
    database_url: str
    database_url_pooled: str

    # Neon Object Storage (S3-compatible)
    aws_region: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_endpoint_url_s3: str | None = None
    s3_bucket_documents: str = "documents"

    # CORS — comma-separated origins
    cors_origins: str = "http://localhost:3000"

    # Upload limits (application defaults)
    max_file_size_bytes: int = 26_214_400  # 25 MiB
    max_files_per_selection: int = 6
    upload_url_expires_seconds: int = 300
    download_url_expires_seconds: int = 300

    # Redis (Phase 4)
    redis_url: str | None = None

    # Inngest
    inngest_app_id: str = "rag-basic"
    inngest_event_key: str | None = None
    inngest_signing_key: str | None = None
    inngest_dev: bool = Field(default=True)

    pinecone_api_key: str | None = None
    openrouter_api_key: str | None = None

    @field_validator("neon_auth_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def allow_sentry_debug(self) -> bool:
        return self.environment in ("development", "test")

    @property
    def jwks_url(self) -> str:
        if self.neon_auth_jwks_url:
            return self.neon_auth_jwks_url
        return f"{self.neon_auth_base_url}/.well-known/jwks.json"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
