"""API Version 1 endpoints."""

from finsignal.api.v1.auth import router as auth_router
from finsignal.api.v1.system import router as system_router

__all__ = ["auth_router", "system_router"]
