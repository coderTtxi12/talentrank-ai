"""Read models for listwise ranking data shown on the recruiter dashboard.

Maps persisted ``ranking_runs``, ``ranking_tournaments``, and ``ranking_results``
rows into API-friendly shapes: tournament orderings (UUID + display name),
Plackett–Luce utilities, and paginated run groupings.
"""

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
    """Flat list of tournaments across all runs (newest first), with total count for UI paging."""

    items: List[RankingTournamentPublic] = Field(default_factory=list)
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)


class RankingPlackettFitSummary(BaseModel):
    """Subset of orchestrator ``plackett_luce.fit`` for the dashboard."""

    converged: Optional[bool] = None
    n_rankings_used: Optional[int] = Field(
        default=None, description="Weighted rankings that entered the PL likelihood."
    )
    note: Optional[str] = None


class RankingPlackettResultPublic(BaseModel):
    """One row from ``ranking_results`` (Plackett–Luce output) for a run."""

    candidate_id: uuid.UUID
    candidate_name: str = Field(description="Resolved full name or short id placeholder.")
    rank_position: int = Field(ge=1)
    utility: float
    posterior_variance: float
    tournaments_seen: int = Field(ge=0)


class RankingRunTournamentsGroup(BaseModel):
    """One ranking run with all its listwise tournaments (for dashboard grouping)."""

    run_id: uuid.UUID
    started_at: datetime
    finished_at: Optional[datetime] = None
    rubric_version: str
    vacancy_id: Optional[uuid.UUID] = None
    pool_size: int = Field(ge=0)
    status: str
    tournaments: List[RankingTournamentPublic] = Field(default_factory=list)
    plackett_results: List[RankingPlackettResultPublic] = Field(
        default_factory=list,
        description="Global PL ranking for this run (empty if PL did not produce results).",
    )
    plackett_fit_summary: Optional[RankingPlackettFitSummary] = Field(
        default=None,
        description="Fit metadata when present on the stored orchestrator output.",
    )


class RankingTournamentsByRunPage(BaseModel):
    """Offset/limit page where each item is one ``RankingRun`` and nested tournaments + PL rows."""

    groups: List[RankingRunTournamentsGroup] = Field(default_factory=list)
    total_runs: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
