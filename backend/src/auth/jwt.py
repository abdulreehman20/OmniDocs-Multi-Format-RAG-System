from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from src.config import get_settings


@lru_cache
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_keys=True)


def verify_access_token(token: str) -> dict[str, Any]:
    """Verify a Bearer JWT. Fail closed on any verification error."""
    settings = get_settings()

    try:
        if settings.environment == "test" and settings.jwt_test_secret:
            claims = jwt.decode(
                token,
                settings.jwt_test_secret,
                algorithms=["HS256"],
                options={"require": ["sub", "exp"]},
            )
        else:
            client = _jwks_client(settings.jwks_url)
            signing_key = client.get_signing_key_from_jwt(token)
            decode_kwargs: dict[str, Any] = {
                "algorithms": ["EdDSA", "RS256", "ES256"],
                "issuer": settings.neon_auth_base_url,
                "options": {"require": ["sub", "exp"]},
            }
            # Audience is optional — only enforce when claim is present after decode
            claims = jwt.decode(token, signing_key.key, **decode_kwargs)
            if "aud" in claims and claims["aud"] not in (
                settings.neon_auth_base_url,
                [settings.neon_auth_base_url],
            ):
                # Allow string or list audiences that include issuer origin
                aud = claims["aud"]
                allowed = {settings.neon_auth_base_url}
                if isinstance(aud, str) and aud not in allowed:
                    raise jwt.InvalidAudienceError("Invalid audience")
                if isinstance(aud, list) and not allowed.intersection(aud):
                    raise jwt.InvalidAudienceError("Invalid audience")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = claims.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims
