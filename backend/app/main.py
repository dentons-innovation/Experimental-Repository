"""FastAPI application factory.

Follows the factory pattern so tests can instantiate the app with
different configurations without import-time side effects.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.middleware import LoggingMiddleware, RequestIDMiddleware, setup_cors
from app.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    OptimisticLockError,
    ValidationError,
)
from app.infrastructure.logging import configure_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown hooks."""
    settings = get_settings()
    logger.info(
        "application_starting",
        env=settings.app_env,
        version=settings.app_version,
    )
    from app.core.database import init_db

    await init_db()

    # ── Real-time infrastructure ─────────────────────────────
    from app.infrastructure.auth import get_jwt_verifier
    from app.infrastructure.realtime.manager import (
        RealtimeConnectionManager,
        RealtimeSubscriptionManager,
    )
    from app.infrastructure.realtime.publisher import InProcessEventPublisher

    conn_manager = RealtimeConnectionManager()
    sub_manager = RealtimeSubscriptionManager()
    publisher = InProcessEventPublisher(sub_manager)

    app.state.realtime_conn_manager = conn_manager
    app.state.realtime_sub_manager = sub_manager
    app.state.realtime_publisher = publisher
    app.state.jwt_verifier = get_jwt_verifier()

    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    configure_logging(
        log_level=settings.log_level,
        json_logs=settings.is_production,
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware (outermost first) ─────────────────────────
    setup_cors(app, settings.cors_origins)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ── Routers ──────────────────────────────────────────────
    app.include_router(health_router)  # /health, /readiness
    app.include_router(api_router)  # /api/v1/...

    # ── WebSocket ────────────────────────────────────────────
    from app.infrastructure.realtime.router import ws_router

    app.include_router(ws_router)

    # ── Exception handlers ───────────────────────────────────
    _register_exception_handlers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": str(exc)}},
        )

    @app.exception_handler(AuthorizationError)
    async def forbidden_handler(
        request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": "FORBIDDEN", "message": str(exc)}},
        )

    @app.exception_handler(AuthenticationError)
    async def unauthorized_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": {"code": "UNAUTHORIZED", "message": str(exc)}},
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": "CONFLICT", "message": str(exc)}},
        )

    @app.exception_handler(OptimisticLockError)
    async def optimistic_lock_handler(
        request: Request, exc: OptimisticLockError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "OPTIMISTIC_LOCK_ERROR",
                    "message": str(exc),
                }
            },
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(exc),
                    "field": exc.field,
                }
            },
        )


# Module-level app instance used by uvicorn
app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
