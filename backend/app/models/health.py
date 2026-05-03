"""Health check response schema for ``GET /api/v1/health``.

Used by load balancers and docker-compose healthchecks to verify the process
is up and optionally to report dependency status in the future.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Coarse readiness: ``ok`` = serving, ``degraded`` / ``down`` = not ready."""

    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class HealthResponse(BaseModel):
    """Schema returned by the health check endpoint."""

    status: HealthStatus = Field(..., description="Overall service status")
    service: str = Field(..., description="Service / project name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Runtime environment")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the health check response",
    )
