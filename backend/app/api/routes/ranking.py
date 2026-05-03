"""Ranking tournaments (listwise) — read-only for recruiter dashboard."""

from __future__ import annotations

import uuid as uuid_mod

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database import Candidate, RankingResult, RankingRun, RankingTournament
from app.schemas.ranking_tournament import (
    RankingPlackettFitSummary,
    RankingPlackettResultPublic,
    RankingRunTournamentsGroup,
    RankingTournamentPublic,
    RankingTournamentsByRunPage,
    RankingTournamentsPage,
)


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


def _plackett_fit_summary_from_run(run: RankingRun) -> RankingPlackettFitSummary | None:
    blob = run.orchestrator_output if isinstance(run.orchestrator_output, dict) else {}
    pl = blob.get("plackett_luce")
    if not isinstance(pl, dict):
        return None
    fit = pl.get("fit")
    if not isinstance(fit, dict):
        return None
    note = fit.get("note")
    n_raw = fit.get("n_rankings_used")
    n_rankings: int | None
    if isinstance(n_raw, bool) or n_raw is None:
        n_rankings = None
    elif isinstance(n_raw, int):
        n_rankings = n_raw
    elif isinstance(n_raw, float) and n_raw == int(n_raw):
        n_rankings = int(n_raw)
    else:
        n_rankings = None
    cv = fit.get("converged")
    converged = cv if isinstance(cv, bool) else None
    return RankingPlackettFitSummary(
        converged=converged,
        n_rankings_used=n_rankings,
        note=str(note) if isinstance(note, str) and note.strip() else None,
    )


def _plackett_display_name(candidate_id: uuid_mod.UUID, full_name: str | None) -> str:
    if isinstance(full_name, str) and full_name.strip():
        return full_name.strip()
    return f"Candidato ({candidate_id.hex[:8]}…)"


def _load_plackett_results_by_run(
    db: Session, run_ids: list[uuid_mod.UUID]
) -> dict[uuid_mod.UUID, list[RankingPlackettResultPublic]]:
    if not run_ids:
        return {}
    rows = db.execute(
        select(
            RankingResult.run_id,
            RankingResult.candidate_id,
            RankingResult.rank_position,
            RankingResult.utility,
            RankingResult.posterior_variance,
            RankingResult.tournaments_seen,
            Candidate.full_name,
        )
        .outerjoin(Candidate, Candidate.id == RankingResult.candidate_id)
        .where(RankingResult.run_id.in_(run_ids))
        .order_by(RankingResult.run_id, RankingResult.rank_position)
    ).all()
    out: dict[uuid_mod.UUID, list[RankingPlackettResultPublic]] = {}
    for rid, cid, pos, util, var, nseen, fname in rows:
        out.setdefault(rid, []).append(
            RankingPlackettResultPublic(
                candidate_id=cid,
                candidate_name=_plackett_display_name(cid, fname),
                rank_position=int(pos),
                utility=float(util),
                posterior_variance=float(var),
                tournaments_seen=int(nseen),
            )
        )
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


def _tournaments_to_public_list(
    db: Session,
    pairs: list[tuple[RankingTournament, RankingRun]],
    run: RankingRun,
) -> list[RankingTournamentPublic]:
    """Build ``RankingTournamentPublic`` rows with name resolution for one run."""

    llm_lists = [[str(x) for x in (tour.llm_ranking or [])] for tour, _ in pairs]
    names_by_id = _load_candidate_names_for_rankings(db, llm_lists)
    out: list[RankingTournamentPublic] = []
    for idx, (tour, _) in enumerate(pairs):
        llm_ids = llm_lists[idx]
        out.append(
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
    return out


@router.get(
    "/tournaments/by-run",
    response_model=RankingTournamentsByRunPage,
    summary="List tournaments grouped by ranking run (paginate runs)",
    description=(
        "Returns the most recent ``RankingRun`` rows first; each group contains all "
        "``ranking_tournaments`` for that run (newest tournament first within the group)."
    ),
)
def list_ranking_tournaments_by_run(
    limit: int = Query(10, ge=1, le=50, description="Max ranking runs per page."),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> RankingTournamentsByRunPage:
    total_raw = db.scalar(select(func.count()).select_from(RankingRun))
    total_runs = int(total_raw or 0)

    run_rows = list(
        db.scalars(
            select(RankingRun)
            .order_by(RankingRun.started_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    if not run_rows:
        return RankingTournamentsByRunPage(
            groups=[],
            total_runs=total_runs,
            offset=offset,
            limit=limit,
        )

    run_ids = [r.id for r in run_rows]
    run_by_id = {r.id: r for r in run_rows}

    trows = db.execute(
        select(RankingTournament, RankingRun)
        .join(RankingRun, RankingRun.id == RankingTournament.run_id)
        .where(RankingTournament.run_id.in_(run_ids))
        .order_by(RankingTournament.created_at.desc())
    ).all()

    from collections import defaultdict

    by_run: dict[uuid_mod.UUID, list[tuple[RankingTournament, RankingRun]]] = defaultdict(list)
    for tour, run in trows:
        by_run[tour.run_id].append((tour, run))

    plackett_by_run = _load_plackett_results_by_run(db, run_ids)

    groups: list[RankingRunTournamentsGroup] = []
    for rid in run_ids:
        run = run_by_id[rid]
        pairs = sorted(
            by_run.get(rid, []),
            key=lambda p: p[0].created_at,
            reverse=True,
        )
        st = run.status.value if hasattr(run.status, "value") else str(run.status)
        groups.append(
            RankingRunTournamentsGroup(
                run_id=run.id,
                started_at=run.started_at,
                finished_at=run.finished_at,
                rubric_version=run.rubric_version,
                vacancy_id=run.vacancy_id,
                pool_size=int(run.pool_size),
                status=st,
                tournaments=_tournaments_to_public_list(db, pairs, run),
                plackett_results=plackett_by_run.get(rid, []),
                plackett_fit_summary=_plackett_fit_summary_from_run(run),
            )
        )

    return RankingTournamentsByRunPage(
        groups=groups,
        total_runs=total_runs,
        offset=offset,
        limit=limit,
    )


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
