"""Proxy helpers for Neon Managed Better Auth (sign-in/up/out + JWT)."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from src.config import Settings

# Cookie we set on the FastAPI response so Swagger/Postman can call /token + /logout.
# Value format: "<neon_cookie_name>=<neon_cookie_value>"
SESSION_COOKIE_NAME = "rag_neon_session"


class NeonAuthError(Exception):
    def __init__(self, status_code: int, detail: Any) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


def _auth_url(settings: Settings, path: str) -> str:
    return f"{settings.neon_auth_base_url.rstrip('/')}/{path.lstrip('/')}"


def _extract_session_pair(response: httpx.Response) -> str | None:
    """Return 'name=value' for the first session-like cookie from Neon."""
    for name, value in response.cookies.items():
        lowered = name.lower()
        if "session" in lowered:
            return f"{name}={value}"
    # Fallback: any cookie set by the auth response
    if response.cookies:
        name, value = next(iter(response.cookies.items()))
        return f"{name}={value}"
    return None


def _raise_from_response(response: httpx.Response) -> None:
    detail: Any
    try:
        detail = response.json()
    except Exception:
        detail = response.text or response.reason_phrase
    if isinstance(detail, dict):
        detail = detail.get("message") or detail.get("error") or detail
    raise NeonAuthError(response.status_code, detail)


def _client() -> httpx.Client:
    return httpx.Client(timeout=30.0, follow_redirects=False)


def fetch_token(settings: Settings, session_cookie_pair: str) -> str:
    with _client() as client:
        response = client.get(
            _auth_url(settings, "token"),
            headers={"Cookie": session_cookie_pair},
        )
    if response.status_code >= 400:
        _raise_from_response(response)
    data = response.json()
    token = data.get("token") if isinstance(data, dict) else None
    if not token or not isinstance(token, str):
        raise NeonAuthError(
            status.HTTP_502_BAD_GATEWAY,
            "Neon Auth /token did not return a JWT",
        )
    return token


def _user_from_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    user = payload.get("user")
    if isinstance(user, dict):
        return user
    # Some responses nest under data.user
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("user"), dict):
        return data["user"]
    return None


def sign_up_email(
    settings: Settings,
    *,
    name: str,
    email: str,
    password: str,
) -> tuple[str, str, dict[str, Any] | None]:
    """Returns (access_token, session_cookie_pair, user)."""
    with _client() as client:
        response = client.post(
            _auth_url(settings, "sign-up/email"),
            json={"name": name, "email": email, "password": password},
        )
    if response.status_code >= 400:
        _raise_from_response(response)
    session_pair = _extract_session_pair(response)
    if not session_pair:
        raise NeonAuthError(
            status.HTTP_502_BAD_GATEWAY,
            "Neon Auth sign-up did not set a session cookie",
        )
    token = fetch_token(settings, session_pair)
    user = _user_from_payload(response.json() if response.content else None)
    return token, session_pair, user


def sign_in_email(
    settings: Settings,
    *,
    email: str,
    password: str,
) -> tuple[str, str, dict[str, Any] | None]:
    """Returns (access_token, session_cookie_pair, user)."""
    with _client() as client:
        response = client.post(
            _auth_url(settings, "sign-in/email"),
            json={"email": email, "password": password},
        )
    if response.status_code >= 400:
        _raise_from_response(response)
    session_pair = _extract_session_pair(response)
    if not session_pair:
        raise NeonAuthError(
            status.HTTP_502_BAD_GATEWAY,
            "Neon Auth sign-in did not set a session cookie",
        )
    token = fetch_token(settings, session_pair)
    user = _user_from_payload(response.json() if response.content else None)
    return token, session_pair, user


def sign_out(settings: Settings, session_cookie_pair: str) -> None:
    with _client() as client:
        response = client.post(
            _auth_url(settings, "sign-out"),
            headers={"Cookie": session_cookie_pair},
        )
    # Treat already-logged-out as success
    if response.status_code >= 400 and response.status_code != 401:
        _raise_from_response(response)


def http_error(exc: NeonAuthError) -> HTTPException:
    code = exc.status_code
    if code < 400 or code > 599:
        code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(status_code=code, detail=exc.detail)
