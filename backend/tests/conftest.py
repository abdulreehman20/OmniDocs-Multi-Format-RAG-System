import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Must run before any src.* import.
os.environ["ENVIRONMENT"] = "test"
os.environ["NEON_AUTH_BASE_URL"] = "https://auth.example.neon.tech/neondb/auth"
os.environ["JWT_TEST_SECRET"] = "test-jwt-secret-do-not-use-in-prod-32b"
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite://",
)
os.environ.setdefault(
    "DATABASE_URL_POOLED",
    "sqlite://",
)
os.environ.setdefault("INNGEST_DEV", "true")
os.environ["SENTRY_DSN"] = ""
os.environ.setdefault("S3_BUCKET_DOCUMENTS", "test-documents")

from src.api import deps as api_deps
from src.config import get_settings
from src.db import models as _models  # noqa: F401
from src.main import app


@pytest.fixture(scope="session")
def settings():
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine) -> Generator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture()
def client(engine, session: Session) -> Generator[TestClient]:
    def _override_session() -> Generator[Session]:
        yield session

    # Reset shared fakes between tests
    api_deps._test_storage = None
    api_deps._test_embeddings = None
    api_deps._test_vectors = None
    app.dependency_overrides[api_deps.get_session] = _override_session
    # Also override the imported get_session used by Depends(get_session)
    from src.db.session import get_session as real_get_session

    app.dependency_overrides[real_get_session] = _override_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    api_deps._test_storage = None
    api_deps._test_embeddings = None
    api_deps._test_vectors = None


def make_token(user_id: str, *, email: str | None = None, expired: bool = False) -> str:
    secret = os.environ["JWT_TEST_SECRET"]
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iss": os.environ["NEON_AUTH_BASE_URL"],
        "iat": now,
        "exp": now - timedelta(minutes=5) if expired else now + timedelta(minutes=15),
    }
    if email:
        payload["email"] = email
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture()
def auth_header_user_a() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token('user-a', email='a@example.com')}"}


@pytest.fixture()
def auth_header_user_b() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token('user-b', email='b@example.com')}"}
