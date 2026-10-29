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
            # Managed Better Auth signs with EdDSA; iss/aud are the Auth URL *origin*
            # (e.g. https://ep-xx.neonauth….neon.tech), not …/neondb/auth.
            issuer = settings.neon_auth_issuer
            client = _jwks_client(settings.jwks_url)
            signing_key = client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["EdDSA", "RS256", "ES256"],
                issuer=issuer,
                audience=issuer,
                options={"require": ["sub", "exp"]},
            )
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
