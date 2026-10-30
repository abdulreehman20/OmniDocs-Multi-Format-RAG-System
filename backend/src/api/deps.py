from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from src.auth.jwt import verify_access_token
from src.config import Settings, get_settings
from src.db.models import User
from src.db.session import get_session
from src.providers.protocols import EmbeddingProvider, ObjectStorage, VectorStore
from src.providers.runtime import get_embedding_provider, get_vector_store
from src.services.users import upsert_user_from_claims

_bearer = HTTPBearer(auto_error=False)

# Shared fake storage for ENVIRONMENT=test so upload + complete share state.
_test_storage: ObjectStorage | None = None
_test_embeddings: EmbeddingProvider | None = None
_test_vectors: VectorStore | None = None


def get_settings_dep() -> Settings:
    return get_settings()


def get_storage(settings: Annotated[Settings, Depends(get_settings_dep)]) -> ObjectStorage:
    global _test_storage
    if settings.environment == "test":
        if _test_storage is None:
            from src.providers.fakes import FakeObjectStorage

            _test_storage = FakeObjectStorage()
        return _test_storage
    from src.db.s3_storage import Boto3ObjectStorage

    return Boto3ObjectStorage(settings)


def get_embeddings(
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> EmbeddingProvider:
    global _test_embeddings
    if settings.environment == "test":
        if _test_embeddings is None:
            from src.providers.fakes import FakeEmbeddingProvider

            _test_embeddings = FakeEmbeddingProvider(
                model_id=settings.embedding_model_id,
                dimension=8,
            )
        return _test_embeddings
    return get_embedding_provider()


def get_vectors(
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> VectorStore:
    global _test_vectors
    if settings.environment == "test":
        if _test_vectors is None:
            from src.providers.fakes import FakeVectorStore

            _test_vectors = FakeVectorStore()
        return _test_vectors
    return get_vector_store()


def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = verify_access_token(credentials.credentials)
    email = claims.get("email")
    # Neon JWT may use "name"; some payloads also include "id" matching sub.
    name = claims.get("name")
    return upsert_user_from_claims(
        session,
        user_id=claims["sub"],
        email=email if isinstance(email, str) else None,
        display_name=name if isinstance(name, str) else None,
    )


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_settings_dep)]
Storage = Annotated[ObjectStorage, Depends(get_storage)]
Embeddings = Annotated[EmbeddingProvider, Depends(get_embeddings)]
Vectors = Annotated[VectorStore, Depends(get_vectors)]
