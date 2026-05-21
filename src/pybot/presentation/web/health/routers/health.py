"""Liveness probe router for Health API.

This module provides the /health endpoint to check if the application process
is alive.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response

from .....dto.health_dto import HealthStatusDTO
from .....services.health import HealthService

router = APIRouter(route_class=DishkaRoute)


@router.head(
    "/",
    status_code=200,
    tags=["health"],
    summary="Liveness probe for HEAD monitors",
    description="Returns an empty OK response for external monitors that use HEAD requests.",
    responses={
        200: {
            "description": "Process is alive.",
        },
    },
)
async def health_head() -> Response:
    """Return empty liveness response for HEAD-only external monitors."""
    return Response(status_code=200)


@router.get(
    "/",
    response_model=HealthStatusDTO,
    response_model_exclude_none=True,
    tags=["health"],
    summary="Liveness probe",
    description="Returns OK if the process is running. No external dependencies are checked.",
    responses={
        200: {
            "description": "Process is alive.",
        },
    },
)
async def health(health_service: FromDishka[HealthService]) -> HealthStatusDTO:
    """Return liveness status of the process.

    Args:
        health_service (HealthService): Health application service resolved from Dishka container.

    Returns:
        HealthStatusDTO: Liveness status payload.
    """
    return await health_service.health()
