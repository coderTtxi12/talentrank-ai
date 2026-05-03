"""Schemas for dev / QA simulation endpoints."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ScreeningSimulationSeedResponse(BaseModel):
    batch_id: str
    inserted_candidates: int
    candidate_ids: List[uuid.UUID]
    breakdown: Dict[str, Any] = Field(default_factory=dict)
