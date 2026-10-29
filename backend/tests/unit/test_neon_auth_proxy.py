from unittest.mock import MagicMock, patch

import httpx
import pytest
from src.services import neon_auth
from src.services.neon_auth import NeonAuthError


def _resp(
    *,
    status_code: int = 200,
    json_data: dict | None = None,
    cookies: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request("POST", "https://example.test/sign-in/email")
    response = httpx.Response(status_code, json=json_data or {}, request=request)
    if cookies:
        for name, value in cookies.items():
            response.cookies.set(name, value)
    return response


def test_extract_session_pair_prefers_session_cookie() -> None:
    response = _resp(cookies={"other": "x", "__Secure-neonauth.session_token": "abc"})
    pair = neon_auth._extract_session_pair(response)
    assert pair == "__Secure-neonauth.session_token=abc"


def test_sign_in_returns_token(settings) -> None:
    sign_in_resp = _resp(
        json_data={"user": {"id": "u1", "email": "a@example.com"}},
        cookies={"better-auth.session_token": "sess"},
    )
    token_resp = _resp(json_data={"token": "jwt-123"})

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = sign_in_resp
    mock_client.get.return_value = token_resp

    with patch("src.services.neon_auth._client", return_value=mock_client):
        token, pair, user = neon_auth.sign_in_email(
            settings,
            email="a@example.com",
            password="password123",
        )

    assert token == "jwt-123"
    assert pair == "better-auth.session_token=sess"
    assert user == {"id": "u1", "email": "a@example.com"}


def test_sign_in_propagates_neon_error(settings) -> None:
    bad = _resp(status_code=401, json_data={"message": "Invalid email or password"})
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = bad

    with patch("src.services.neon_auth._client", return_value=mock_client):
        with pytest.raises(NeonAuthError) as exc:
            neon_auth.sign_in_email(settings, email="a@example.com", password="nope")
    assert exc.value.status_code == 401


def test_auth_routes_sign_in_and_authorize(client, settings) -> None:
    sign_in_resp = _resp(
        json_data={"user": {"id": "user-a", "email": "a@example.com"}},
        cookies={"better-auth.session_token": "sess"},
    )
    token_resp = _resp(json_data={"token": "jwt-abc"})

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = sign_in_resp
    mock_client.get.return_value = token_resp

    with patch("src.services.neon_auth._client", return_value=mock_client):
        response = client.post(
            "/api/v1/auth/sign-in",
            json={"email": "a@example.com", "password": "password123"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "jwt-abc"
    assert body["token_type"] == "bearer"
    assert response.cookies.get(neon_auth.SESSION_COOKIE_NAME)


def test_token_requires_cookie(client) -> None:
    response = client.get("/api/v1/auth/token")
    assert response.status_code == 401
