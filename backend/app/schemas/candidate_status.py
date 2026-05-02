"""Request / response for manual status change."""

from pydantic import BaseModel, Field


class PatchCandidateStatusRequest(BaseModel):
    status: str = Field(min_length=1, max_length=64)
    reason: str | None = Field(default=None, max_length=2000)
