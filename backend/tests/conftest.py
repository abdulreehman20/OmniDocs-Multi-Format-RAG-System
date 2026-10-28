import os

# Must run before any src.* import so Settings and auth see test values.
# Force test env so local .env / shell development settings cannot trigger PropelAuth network I/O.
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("PROPELAUTH_AUTH_URL", "https://auth.example.com")
os.environ.setdefault("PROPELAUTH_API_KEY", "test-api-key")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/rag_basic_test",
)
os.environ.setdefault(
    "DATABASE_URL_POOLED",
    "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/rag_basic_test",
)
os.environ.setdefault("INNGEST_DEV", "true")
# Override .env so tests never initialize/send to Sentry.
os.environ["SENTRY_DSN"] = ""



import pytest
from fastapi.testclient import TestClient
from src.config import get_settings
from src.main import app


@pytest.fixture(scope="session")
def settings():
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
