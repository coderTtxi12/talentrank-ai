"""Schemas for enqueueing listwise ranking jobs."""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class CreateListwiseJobRequest(BaseModel):
    """Optional vacancy scope; when set, only candidates linked to that vacancy are ranked."""

    vacancy_id: Optional[uuid.UUID] = Field(
        default=None,
        description="If provided, restrict cohort to candidates with a conversation on this vacancy.",
    )


class CreateListwiseJobResponse(BaseModel):
    job_id: uuid.UUID
    status: str = Field(default="pending", description="Initial queue status.")
    listen_channel: str = Field(
        default="listwise_job_pending",
        description="Postgres NOTIFY channel workers subscribe to.",
    )
