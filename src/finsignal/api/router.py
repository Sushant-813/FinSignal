"""API router assembly for FinSignal."""

from fastapi import APIRouter

from finsignal.api.v1.system import router as system_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(system_router)
