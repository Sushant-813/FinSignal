"""FinSignal application factory and entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from finsignal.api.router import api_v1_router
from finsignal.api.v1.system import router as system_router
from finsignal.common.exceptions import FinSignalError
from finsignal.common.handlers import (
    finsignal_exception_handler,
    sqlalchemy_exception_handler,
    starlette_http_exception_handler,
    validation_exception_handler,
)
from finsignal.core import database
from finsignal.core.config import Settings, get_settings
from finsignal.core.logging import setup_logging
from finsignal.core.middleware import RequestIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    # Startup phase
    yield
    # Shutdown phase: Cleanly dispose of the application-bound database engine
    if hasattr(app.state, "db_engine") and app.state.db_engine is not None:
        await app.state.db_engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct and configure a FinSignal FastAPI application instance.

    Acts as the composition root, wiring logging, middleware, exception handlers,
    routers, and application-bound resources.
    """
    app_settings = settings or get_settings()

    # Idempotent logging configuration
    setup_logging(app_settings)

    app = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    # Initialize and bind database resources to app.state
    engine, session_maker = database.create_db_resources(app_settings)
    app.state.settings = app_settings
    app.state.db_engine = engine
    app.state.session_maker = session_maker

    # Attach pure ASGI Request-ID and unexpected exception middleware
    app.add_middleware(RequestIdMiddleware, header_name=app_settings.request_id_header)

    # Register specific FastAPI exception handlers (Layer 2)
    # Note: No generic handler for Exception is registered to avoid competing fallback handlers;
    # unexpected errors escaping the app boundary are handled cleanly by RequestIdMiddleware (Layer 1).
    app.add_exception_handler(FinSignalError, finsignal_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)  # type: ignore[arg-type]

    # Mount system probes at root / for Phase 0 contract compatibility (/health, /ready)
    app.include_router(system_router)

    # Mount versioned API routes (/api/v1/...)
    app.include_router(api_v1_router)

    return app


# Module-level application instance for ASGI servers (e.g. uvicorn finsignal.main:app)
app = create_app()
