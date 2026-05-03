"""Request body for recruiter-driven **PATCH** of a candidate pipeline status.

Allows moving a candidate to an explicit workflow state with an optional audit
reason (stored or logged per route implementation).
"""

from pydantic import BaseModel, Field


class PatchCandidateStatusRequest(BaseModel):
    """Target ``CandidateStatus`` value as string plus optional human-readable reason."""

    status: str = Field(min_length=1, max_length=64)
    reason: str | None = Field(default=None, max_length=2000)
