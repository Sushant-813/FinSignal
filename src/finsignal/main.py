"""FinSignal application factory and entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

from finsignal.core import database
from finsignal.core.config import Settings, get_settings


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

    Accepts optional settings to allow clean test database isolation.
    """
    app_settings = settings or get_settings()

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

    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        """Process liveness probe; independent of database connectivity."""
        return {"status": "healthy"}

    @app.get("/ready", tags=["System"], response_model=None)
    async def readiness_check() -> Response:
        """Infrastructure readiness probe; verifies downstream database availability."""
        is_ready = await database.ping_database(app.state.db_engine)
        if is_ready:
            return JSONResponse(
                status_code=200,
                content={"status": "ready", "database": "connected"},
            )
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"},
        )

    return app


# Module-level application instance for ASGI servers (e.g. uvicorn finsignal.main:app)
app = create_app()
