"""Ranking tournaments (listwise) — read-only for recruiter dashboard."""

from __future__ import annotations

import uuid as uuid_mod

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database import Candidate, RankingRun, RankingTournament
from app.schemas.ranking_tournament import RankingTournamentPublic, RankingTournamentsPage


def _llm_ranking_display_names(
    llm_ranking: list[str],
    names_by_id: dict[uuid_mod.UUID, str | None],
) -> list[str]:
    if not llm_ranking:
        return []

    out: list[str] = []
    for raw in llm_ranking:
        try:
            uid = uuid_mod.UUID(str(raw))
        except (ValueError, TypeError):
            out.append(str(raw))
            continue
        name = names_by_id.get(uid)
        if isinstance(name, str) and name.strip():
            out.append(name.strip())
        else:
            out.append(f"Candidato ({uid.hex[:8]}…)")
    return out


def _load_candidate_names_for_rankings(
    db: Session, all_llm_rankings: list[list[str]]
) -> dict[uuid_mod.UUID, str | None]:
    need: set[uuid_mod.UUID] = set()
    for rank in all_llm_rankings:
        for raw in rank:
            try:
                need.add(uuid_mod.UUID(str(raw)))
            except (ValueError, TypeError):
                pass
    if not need:
        return {}
    rows = db.execute(
        select(Candidate.id, Candidate.full_name).where(Candidate.id.in_(need))
    ).all()
    return {r[0]: r[1] for r in rows}

router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.get(
    "/tournaments",
    response_model=RankingTournamentsPage,
    summary="List ranking tournaments (paginated)",
    description=(
        "Paginated ``ranking_tournaments`` (newest first), with run context. "
        "Use query params ``offset`` and ``limit``."
    ),
)
def list_ranking_tournaments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> RankingTournamentsPage:
    total_raw = db.scalar(select(func.count()).select_from(RankingTournament))
    total = int(total_raw or 0)

    stmt = (
        select(RankingTournament, RankingRun)
        .join(RankingRun, RankingRun.id == RankingTournament.run_id)
        .order_by(RankingTournament.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    llm_lists = [[str(x) for x in (tour.llm_ranking or [])] for tour, _ in rows]
    names_by_id = _load_candidate_names_for_rankings(db, llm_lists)

    items: list[RankingTournamentPublic] = []
    for idx, (tour, run) in enumerate(rows):
        llm_ids = llm_lists[idx]
        items.append(
            RankingTournamentPublic(
                id=tour.id,
                run_id=tour.run_id,
                vacancy_id=run.vacancy_id,
                rubric_version=run.rubric_version,
                candidate_ids=[str(x) for x in (tour.candidate_ids or [])],
                llm_ranking=llm_ids,
                llm_ranking_names=_llm_ranking_display_names(llm_ids, names_by_id),
                confidence=float(tour.confidence),
                model=tour.model,
                is_active_learning=bool(tour.is_active_learning),
                llm_trace=dict(tour.llm_trace or {}),
                created_at=tour.created_at,
            )
        )
    return RankingTournamentsPage(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )
