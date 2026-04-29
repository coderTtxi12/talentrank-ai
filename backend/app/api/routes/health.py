from fastapi import APIRouter, status

from app.core.config import settings
from app.models.health import HealthResponse, HealthStatus

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service health check",
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status=HealthStatus.OK,
        service=settings.PROJECT_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
