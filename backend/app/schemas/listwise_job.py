"""Request and response models for **POST** enqueue of listwise ranking jobs.

Clients create a ``jobs`` row with ``job_type=listwise``; workers react via
``NOTIFY`` on ``listen_channel``.
"""

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
    """Acknowledgement after enqueue: new job id, initial status, NOTIFY channel name."""

    job_id: uuid.UUID
    status: str = Field(default="pending", description="Initial queue status.")
    listen_channel: str = Field(
        default="listwise_job_pending",
        description="Postgres NOTIFY channel workers subscribe to.",
    )
