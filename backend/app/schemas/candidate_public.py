"""Pydantic schemas for candidate listings (dashboard / API responses).

Aligned with the recruiter dashboard shape; ORM fields are mapped with defaults
where the screening schema does not yet duplicate legacy loan-style columns.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CandidatePublic(BaseModel):
    """Single candidate row as consumed by the dashboard."""

    id: str
    country_code: Literal["ES", "MX"]
    document_type: Literal["DNI", "CURP", "CC", "CPF"] = "CURP"
    document_number: str = ""
    full_name: str = ""
    drivers_license: Optional[bool] = None
    city_zone: Optional[str] = None
    availability: Optional[str] = None
    preferred_schedule: Optional[str] = None
    experience_years: Optional[int] = None
    platforms: Optional[List[str]] = None
    start_date: Optional[date] = None
    amount_requested: float = 0.0
    currency: str = "USD"
    monthly_income: float = 0.0
    status: str
    risk_score: Optional[float] = None
    requires_review: bool = False
    banking_info: Optional[dict] = None
    # Latest sentiment_results row (GET one candidate): classification + confidence + signals JSON.
    sentiment: Optional[str] = Field(
        default=None,
        description="sentiment_results.sentiment enum value (e.g. positive, neutral).",
    )
    sentiment_confidence: Optional[float] = Field(
        default=None,
        description="sentiment_results.confidence (typically 0–1).",
    )
    sentiment_signals: Optional[Dict[str, Any]] = None
    extra_data: Optional[dict] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    created_by_id: Optional[str] = None
    reviewed_by_id: Optional[str] = None

    model_config = {"from_attributes": False}


class CandidatesCursorPage(BaseModel):
    """Cursor-paginated candidate list: stable ordering, opaque ``next_cursor`` token.

    See ``ENDPOINT_RULES.md`` for cursor encoding and filter semantics.
    """

    items: list[CandidatePublic]
    next_cursor: Optional[str] = None
    limit: int
    total: Optional[int] = Field(
        default=None,
        description="Row count for current filters (only when include_total was requested).",
    )
