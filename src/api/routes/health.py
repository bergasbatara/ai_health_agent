from __future__ import annotations

from fastapi import APIRouter

from api.models import HealthResponse


health_router = APIRouter(tags=["health"])


@health_router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse()
