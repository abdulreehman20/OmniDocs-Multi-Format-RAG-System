from propelauth_fastapi import init_auth

from src.config import get_settings

settings = get_settings()

auth = init_auth(settings.propelauth_auth_url, settings.propelauth_api_key)
