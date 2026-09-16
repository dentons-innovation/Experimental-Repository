"""FastAPI middleware stack.

Middleware is applied in reverse order (last registered = first executed).
Applied order when request comes in:
  1. RequestIDMiddleware   — attach X-Request-ID
  2. LoggingMiddleware     — structured request/response logging
  3. CORSMiddleware        — CORS headers
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import structlog

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and response.

    Reads X-Request-ID from the incoming request if present (forwarded
    from an upstream proxy), otherwise generates a new UUID4.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # Bind to structlog context for all log lines in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured access log for every HTTP request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        log = logger.bind(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_host=request.client.host if request.client else None,
        )

        if response.status_code >= 500:
            log.error("request_completed")
        elif response.status_code >= 400:
            log.warning("request_completed")
        else:
            log.info("request_completed")

        return response


def setup_cors(app: "FastAPI", allowed_origins: list[str] | str) -> None:  # type: ignore[name-defined]  # noqa: F821
    """Configure CORS middleware with secure defaults."""
    if isinstance(allowed_origins, str):
        origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
    else:
        origins = list(allowed_origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Total-Count"],
        max_age=600,
    )
