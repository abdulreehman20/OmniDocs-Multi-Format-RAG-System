from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
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

    # Postgres — pooled may be omitted; defaults to DATABASE_URL
    database_url: str
    database_url_pooled: str | None = None

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

    # OpenRouter (embeddings Phase 2; chat Phase 3)
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    embedding_model_id: str = "nvidia/nemotron-3.5-embed-1b:free"
    embedding_dimension: int = 2048

    # Pinecone (document-schema index; dense field must match index schema)
    pinecone_api_key: str | None = None
    pinecone_index_host: str | None = None
    pinecone_index_name: str | None = None
    pinecone_dense_field: str = "embeddings"

    # Chat / RAG (Phase 3)
    chat_model_id: str = "nvidia/nemotron-3.5-lightning:free"
    max_selected_documents_per_chat: int = 6
    max_history_messages: int = 12
    max_retrieval_candidates: int = 25
    max_context_chunks: int = 5
    max_context_tokens: int = 3000
    # LLM HTTP read timeout; free OpenRouter models can be slow to first token.
    chat_stream_timeout_seconds: int = 180
    # How long the SSE request waits for Inngest embed+search before generating.
    chat_retrieval_timeout_seconds: int = 120
    # Legacy alias; unused when generation streams on the request path.
    chat_bridge_timeout_seconds: int | None = None

    # Ingestion / chunking
    chunker_version: str = "langchain-recursive-v1"
    parser_version: str = "langchain-loaders-v1"
    ingestion_embed_batch_size: int = 32
    ingestion_max_concurrency_per_user: int = 1
    chunk_size_markdown: int = 700
    chunk_overlap_markdown: int = 100
    chunk_size_text: int = 750
    chunk_overlap_text: int = 100
    chunk_size_pdf: int = 850
    chunk_overlap_pdf: int = 120
    chunk_size_docx: int = 700
    chunk_overlap_docx: int = 100
    csv_rows_per_chunk: int = 40


    @field_validator("neon_auth_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator(
        "pinecone_api_key",
        "pinecone_index_host",
        "pinecone_index_name",
        "openrouter_api_key",
        mode="before",
    )
    @classmethod
    def strip_optional_quotes(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().strip("\"'")
        return value

    @model_validator(mode="after")
    def default_pooled_database_url(self) -> "Settings":
        if not self.database_url_pooled:
            self.database_url_pooled = self.database_url
        return self

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
    def neon_auth_issuer(self) -> str:
        """JWT iss/aud for Managed Better Auth is the URL origin, not the /auth path.

        Neon docs: if base URL is https://ep-xx…/neondb/auth, iss/aud are https://ep-xx…
        """
        parsed = urlparse(self.neon_auth_base_url)
        if not parsed.scheme or not parsed.netloc:
            return self.neon_auth_base_url
        return f"{parsed.scheme}://{parsed.netloc}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


_settings: Settings | None = None
_settings_env_mtime: float | None = None


def _env_file_mtime() -> float | None:
    # config.py lives in src/; .env is loaded from backend/ cwd (and optionally beside it)
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if candidate.is_file():
            return candidate.stat().st_mtime
    return None


def get_settings() -> Settings:
    """Load settings; re-read when backend/.env changes (dev-friendly)."""
    global _settings, _settings_env_mtime
    mtime = _env_file_mtime()
    if _settings is None or mtime != _settings_env_mtime:
        _settings = Settings()
        _settings_env_mtime = mtime
    return _settings


def get_settings_cache_clear() -> None:
    """Test helper — mirrors former get_settings.cache_clear()."""
    global _settings, _settings_env_mtime
    _settings = None
    _settings_env_mtime = None


# Back-compat for tests that call get_settings.cache_clear()
get_settings.cache_clear = get_settings_cache_clear  # type: ignore[attr-defined]
