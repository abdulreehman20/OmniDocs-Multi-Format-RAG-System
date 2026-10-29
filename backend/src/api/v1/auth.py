from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from src.api.deps import AppSettings
from src.schemas.auth import (
    MessageResponse,
    SignInRequest,
    SignUpRequest,
    TokenResponse,
)
from src.services import neon_auth
from src.services.neon_auth import SESSION_COOKIE_NAME, NeonAuthError, http_error

router = APIRouter(prefix="/auth", tags=["auth"])

_SESSION_MAX_AGE = 60 * 60 * 24 * 7


def _set_session_cookie(response: Response, session_pair: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_pair,
        httponly=True,
        samesite="lax",
        max_age=_SESSION_MAX_AGE,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


@router.post("/sign-up", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def sign_up(
    body: SignUpRequest,
    settings: AppSettings,
    response: Response,
) -> TokenResponse:
    """Proxy Neon Auth sign-up; returns a Bearer JWT for FastAPI / Swagger Authorize."""
    try:
        token, session_pair, user = neon_auth.sign_up_email(
            settings,
            name=body.name,
            email=str(body.email),
            password=body.password,
        )
    except NeonAuthError as exc:
        raise http_error(exc) from exc
    _set_session_cookie(response, session_pair)
    return TokenResponse(access_token=token, user=user)


@router.post("/sign-in", response_model=TokenResponse)
def sign_in(
    body: SignInRequest,
    settings: AppSettings,
    response: Response,
) -> TokenResponse:
    """Proxy Neon Auth sign-in; returns a Bearer JWT for FastAPI / Swagger Authorize."""
    try:
        token, session_pair, user = neon_auth.sign_in_email(
            settings,
            email=str(body.email),
            password=body.password,
        )
    except NeonAuthError as exc:
        raise http_error(exc) from exc
    _set_session_cookie(response, session_pair)
    return TokenResponse(access_token=token, user=user)


@router.post("/sign-out", response_model=MessageResponse)
def sign_out(
    settings: AppSettings,
    response: Response,
    rag_neon_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> MessageResponse:
    """Proxy Neon Auth sign-out and clear the local session cookie."""
    if rag_neon_session:
        try:
            neon_auth.sign_out(settings, rag_neon_session)
        except NeonAuthError as exc:
            raise http_error(exc) from exc
    _clear_session_cookie(response)
    return MessageResponse(message="Signed out")


@router.get("/token", response_model=TokenResponse)
def get_token(
    settings: AppSettings,
    rag_neon_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> TokenResponse:
    """Exchange the session cookie (from sign-in/sign-up) for a fresh JWT."""
    if not rag_neon_session:
        raise http_error(
            NeonAuthError(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
        )
    try:
        token = neon_auth.fetch_token(settings, rag_neon_session)
    except NeonAuthError as exc:
        raise http_error(exc) from exc
    return TokenResponse(access_token=token)
