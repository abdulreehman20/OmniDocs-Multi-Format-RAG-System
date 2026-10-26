from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "backend"
    environment: str = "development"  # development | staging | production
    debug: bool = False

    # Sentry
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 1.0
    sentry_profiles_sample_rate: float = 1.0

    # Propel Auth
    propelauth_auth_url: str
    propelauth_api_key: str

    # Postgres
    database_url: str
    database_url_pooled: str
    
    # Later: database_url: str = "sqlite:///./app.db"
    # Later: openai_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()