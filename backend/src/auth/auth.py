from types import SimpleNamespace

from propelauth_fastapi import init_auth

from src.config import get_settings

settings = get_settings()


class _TestAuth:
    """Offline stand-in so ENVIRONMENT=test can import the app without PropelAuth network I/O."""

    @staticmethod
    def require_user() -> SimpleNamespace:
        return SimpleNamespace(
            user_id="test-user-id",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )


if settings.environment == "test":
    auth = _TestAuth()
else:
    auth = init_auth(settings.propelauth_auth_url, settings.propelauth_api_key)
