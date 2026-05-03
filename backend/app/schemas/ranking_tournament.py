"""Public schema for listwise / ranking tournament rows (dashboard read)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RankingTournamentPublic(BaseModel):
    """One row from ``ranking_tournaments`` plus run context."""

    id: uuid.UUID
    run_id: uuid.UUID
    vacancy_id: Optional[uuid.UUID] = None
    rubric_version: Optional[str] = None
    candidate_ids: List[str] = Field(default_factory=list)
    llm_ranking: List[str] = Field(default_factory=list)
    llm_ranking_names: List[str] = Field(
        default_factory=list,
        description="Display names for llm_ranking (same order); unknown ids get a short placeholder.",
    )
    confidence: float
    model: str
    is_active_learning: bool
    llm_trace: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RankingTournamentsPage(BaseModel):
    """Offset/limit page of tournaments (newest first globally)."""

    items: List[RankingTournamentPublic] = Field(default_factory=list)
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
