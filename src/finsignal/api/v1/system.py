"""System health and readiness probe endpoints."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from finsignal.core import database

router = APIRouter(tags=["System"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Process liveness probe; independent of database connectivity."""
    return {"status": "healthy"}


@router.get("/ready", response_model=None)
async def readiness_check(request: Request) -> Response:
    """Infrastructure readiness probe; verifies downstream database availability."""
    db_engine = getattr(request.app.state, "db_engine", None)
    if db_engine is None:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"},
        )

    is_ready = await database.ping_database(db_engine)
    if is_ready:
        return JSONResponse(
            status_code=200,
            content={"status": "ready", "database": "connected"},
        )
    return JSONResponse(
        status_code=503,
        content={"status": "unhealthy", "database": "disconnected"},
    )
