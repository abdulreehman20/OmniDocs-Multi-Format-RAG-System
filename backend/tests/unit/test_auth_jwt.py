import jwt
import pytest
from fastapi import HTTPException
from src.auth.jwt import verify_access_token
from src.db.models import User

from tests.conftest import make_token


def test_verify_valid_test_token() -> None:
    token = make_token("user-1", email="u@example.com")
    claims = verify_access_token(token)
    assert claims["sub"] == "user-1"


def test_verify_expired_token() -> None:
    token = make_token("user-1", expired=True)
    with pytest.raises(HTTPException) as exc:
        verify_access_token(token)
    assert exc.value.status_code == 401


def test_verify_forged_signature() -> None:
    token = jwt.encode(
        {"sub": "user-1", "exp": 9999999999},
        "wrong-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        verify_access_token(token)
    assert exc.value.status_code == 401


def test_authenticated_request_upserts_app_user(client, session, auth_header_user_a) -> None:
    assert session.get(User, "user-a") is None

    response = client.get("/api/v1/limits", headers=auth_header_user_a)
    assert response.status_code == 200

    user = session.get(User, "user-a")
    assert user is not None
    assert user.email == "a@example.com"


def test_authenticated_request_updates_existing_user(client, session, auth_header_user_a) -> None:
    session.add(User(id="user-a", email="old@example.com", display_name="Old"))
    session.commit()

    response = client.get("/api/v1/limits", headers=auth_header_user_a)
    assert response.status_code == 200

    user = session.get(User, "user-a")
    assert user is not None
    assert user.email == "a@example.com"
