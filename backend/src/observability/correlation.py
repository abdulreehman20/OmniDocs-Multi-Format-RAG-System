from __future__ import annotations

import contextvars
import re
from uuid import uuid4

import sentry_sdk

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

_REDACT_KEYS = re.compile(
    r"(authorization|cookie|set-cookie|x-api-key|api[_-]?key|secret|password|token)",
    re.IGNORECASE,
)
_SIGNED_URL = re.compile(r"(X-Amz-Signature|Signature=|X-Amz-Credential)", re.IGNORECASE)


def new_request_id() -> str:
    return str(uuid4())


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(value: str) -> None:
    _request_id.set(value)


def redact_value(key: str, value: str) -> str:
    if _REDACT_KEYS.search(key):
        return "[REDACTED]"
    if _SIGNED_URL.search(value):
        return "[REDACTED_SIGNED_URL]"
    if value.lower().startswith("bearer "):
        return "Bearer [REDACTED]"
    return value


def set_sentry_context(
    *,
    request_id: str | None = None,
    user_id: str | None = None,
    document_id: str | None = None,
    job_id: str | None = None,
    inngest_run_id: str | None = None,
    message_id: str | None = None,
    conversation_id: str | None = None,
) -> None:
    scope = sentry_sdk.get_current_scope()
    tags: dict[str, str] = {}
    if request_id:
        tags["request_id"] = request_id
    if user_id:
        tags["user_id"] = user_id
        scope.set_user({"id": user_id})
    if document_id:
        tags["document_id"] = document_id
    if job_id:
        tags["job_id"] = job_id
    if inngest_run_id:
        tags["inngest_run_id"] = inngest_run_id
    if message_id:
        tags["message_id"] = message_id
    if conversation_id:
        tags["conversation_id"] = conversation_id
    for k, v in tags.items():
        scope.set_tag(k, v)
    if tags:
        scope.set_context("correlation", tags)


def before_send_filter(event: dict, hint: dict) -> dict | None:
    """Strip obvious secrets from Sentry events."""
    _ = hint
    request = event.get("request") or {}
    headers = request.get("headers")
    if isinstance(headers, dict):
        request["headers"] = {
            k: redact_value(k, str(v)) for k, v in headers.items()
        }
        event["request"] = request
    return event
