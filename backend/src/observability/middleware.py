from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.observability.correlation import (
    get_request_id,
    new_request_id,
    set_request_id,
    set_sentry_context,
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        incoming = request.headers.get("x-request-id")
        request_id = incoming.strip() if incoming and incoming.strip() else new_request_id()
        set_request_id(request_id)
        set_sentry_context(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-Id"] = get_request_id() or request_id
        return response
