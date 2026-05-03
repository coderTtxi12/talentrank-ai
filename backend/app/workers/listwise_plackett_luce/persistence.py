"""Persist listwise orchestrator + sub-agent outputs into normalized ranking tables.

Writes:
  * ``ranking_runs`` — one row per job execution (orchestrator summary in JSONB).
  * ``ranking_tournaments`` — one row per sub-agent / tool call (ordering + trace).
  * ``ranking_results`` — one row per cohort candidate after Plackett–Luce fit on tournament orders.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.database import JobStatus, RankingResult, RankingRun, RankingTournament
from app.workers.listwise_plackett_luce.plackett_luce_fit import (
    approximate_posterior_variance_heuristic,
    fit_plackett_luce_utilities,
)
from app.workers.listwise_plackett_luce.subagent import validate_uuid_list

logger = get_logger(__name__)

RUBRIC_LISTWISE_ORCH_V1 = "listwise_orchestrator_v1"


def _uuid_list(raw: List[Any]) -> List[uuid.UUID]:
    return [uuid.UUID(x) for x in validate_uuid_list([str(x) for x in raw])]


def _normalize_ordering(ordered: List[uuid.UUID], pool: List[uuid.UUID]) -> List[uuid.UUID]:
    pool_set = set(pool)
    out: List[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for x in ordered:
        if x in pool_set and x not in seen:
            out.append(x)
            seen.add(x)
    for x in pool:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def persist_listwise_orch_and_tournaments(
    db: Session,
    *,
    job_id: uuid.UUID,
    vacancy_id: Optional[uuid.UUID],
    cohort_ids: List[uuid.UUID],
    orch: Dict[str, Any],
    model_label: str,
) -> uuid.UUID:
    """Insert ``RankingRun`` + ``RankingTournament`` rows. Caller commits."""

    raw_tournaments = orch.get("tournaments") or []
    if not isinstance(raw_tournaments, list):
        logger.warning(
            "PL persist: orch['tournaments'] is not a list type=%s — using empty",
            type(raw_tournaments),
        )
        raw_tournaments = []
    pool_n = len(cohort_ids)
    logger.info(
        "PL persist: ranking_run draft job_id=%s vacancy_id=%s cohort=%d orch_tournaments=%d model=%s",
        job_id,
        vacancy_id,
        pool_n,
        len(raw_tournaments),
        model_label[:80],
    )
    orch_blob: Dict[str, Any] = {
        "source_job_id": str(job_id),
        "final_summary": orch.get("final_summary"),
        "coverage": orch.get("coverage"),
        "orch_steps_used": orch.get("orch_steps_used"),
        "cohort_candidate_ids": [str(c) for c in cohort_ids],
    }
    if orch.get("error"):
        orch_blob["error"] = orch.get("error")

    run = RankingRun(
        vacancy_id=vacancy_id,
        rubric_version=RUBRIC_LISTWISE_ORCH_V1,
        pool_size=pool_n,
        top_n=pool_n,
        status=JobStatus.DONE,
        finished_at=datetime.now(timezone.utc),
        orchestrator_output=orch_blob,
    )
    db.add(run)
    db.flush()
    logger.info(
        "PL persist: flushed RankingRun run_id=%s pool_size=%s",
        run.id,
        pool_n,
    )

    persisted_n = 0
    for idx, entry in enumerate(raw_tournaments):
        if not isinstance(entry, dict):
            logger.warning("PL persist: skip tournament idx=%d expected dict got %s", idx, type(entry))
            continue
        raw_cids = entry.get("candidate_ids") or []
        if not isinstance(raw_cids, list):
            raw_cids = []
        pool = _uuid_list(raw_cids)
        if not pool:
            logger.warning(
                "PL persist: skip tournament idx=%d empty pool after UUID validation",
                idx,
            )
            continue

        instructions = str(entry.get("instructions") or "")
        res: Dict[str, Any] = entry.get("result") if isinstance(entry.get("result"), dict) else {}

        skipped = bool(res.get("skipped")) or bool(res.get("error"))
        if skipped:
            llm_ranking = list(pool)
            conf = 0.0
        else:
            ordered_raw = res.get("ordered_candidate_ids") or []
            if not isinstance(ordered_raw, list):
                ordered_raw = []
            ordered = _uuid_list(ordered_raw)
            llm_ranking = _normalize_ordering(ordered, pool)
            conf = 1.0

        trace: Dict[str, Any] = {
            "orchestrator_instructions": instructions,
            "subagent_rationale": res.get("rationale"),
            "skipped": skipped,
            "error": res.get("error"),
            "raw_ordered_candidate_ids": res.get("ordered_candidate_ids"),
        }

        db.add(
            RankingTournament(
                run_id=run.id,
                candidate_ids=pool,
                llm_ranking=llm_ranking,
                confidence=conf,
                model=model_label[:120],
                is_active_learning=False,
                llm_trace=trace,
            )
        )
        persisted_n += 1
        logger.info(
            "PL persist: queued RankingTournament idx=%d run_id=%s pool=%d skipped=%s conf=%s ranking_len=%d",
            idx,
            run.id,
            len(pool),
            skipped,
            conf,
            len(llm_ranking),
        )
        logger.debug(
            "PL persist: tournament idx=%d trace_skipped=%s llm_ranking_prefix=%s",
            idx,
            trace.get("skipped"),
            [str(x) for x in llm_ranking[:12]],
        )

    # Required when Session.autoflush is False (worker SessionLocal): SELECT in
    # ``apply_plackett_luce_for_run`` must see rows in the same transaction.
    db.flush()
    logger.info(
        "PL persist: flushed RankingTournament pending rows for run_id=%s count=%s",
        run.id,
        persisted_n,
    )

    logger.info(
        "PL persist: prepared %d RankingTournament rows for run_id=%s (caller commits)",
        persisted_n,
        run.id,
    )
    return run.id


def apply_plackett_luce_for_run(
    db: Session,
    *,
    run_id: uuid.UUID,
    cohort_ids: List[uuid.UUID],
) -> Dict[str, Any]:
    """Fit Plackett–Luce only from mini-tournament orderings already persisted.

    ``RankingResult`` rows are written **only** for candidates who appear in at least one
    ranking that contributes to the PL likelihood (same filters as ``weighted_rankings``:
    tournament not skipped, confidence > 0, at least two distinct IDs in ``llm_ranking``).
    """

    run = db.get(RankingRun, run_id)
    if run is None:
        logger.error("PL apply: RankingRun missing run_id=%s", run_id)
        return {"error": "run_not_found", "run_id": str(run_id)}

    logger.info(
        "PL apply: start run_id=%s cohort_requested=%d",
        run_id,
        len(cohort_ids),
    )

    tournaments = db.scalars(
        select(RankingTournament).where(RankingTournament.run_id == run_id)
    ).all()
    logger.info("PL apply: loaded RankingTournament rows n=%d", len(tournaments))

    weighted_rankings: List[Tuple[List[uuid.UUID], float]] = []
    appearances: Counter[str] = Counter()
    skipped_trace = 0
    skipped_conf = 0
    skipped_short_ranking = 0

    for t in tournaments:
        pool = list(t.candidate_ids) if t.candidate_ids else []
        ranking = list(t.llm_ranking) if t.llm_ranking else []
        for cid in pool:
            appearances[str(cid)] += 1
        trace = t.llm_trace if isinstance(t.llm_trace, dict) else {}
        if trace.get("skipped"):
            skipped_trace += 1
            continue
        wt = float(t.confidence or 0)
        if wt <= 0:
            skipped_conf += 1
            continue
        if len(ranking) < 2:
            skipped_short_ranking += 1
            continue
        weighted_rankings.append((ranking, wt))

    logger.info(
        "PL apply: building likelihood from tournaments → eligible_rankings=%d "
        "(skipped trace=%d conf<=0=%d len<2=%d)",
        len(weighted_rankings),
        skipped_trace,
        skipped_conf,
        skipped_short_ranking,
    )

    cohort_set = set(cohort_ids)
    filtered_rankings: List[Tuple[List[uuid.UUID], float]] = []
    for order, wt in weighted_rankings:
        seen: set[uuid.UUID] = set()
        filt: List[uuid.UUID] = []
        for x in order:
            if x not in cohort_set or x in seen:
                continue
            filt.append(x)
            seen.add(x)
        if len(filt) >= 2:
            filtered_rankings.append((filt, wt))
    weighted_rankings = filtered_rankings
    logger.info(
        "PL apply: after cohort filter weighted_rankings=%d (cohort_set=%d)",
        len(weighted_rankings),
        len(cohort_set),
    )

    ids_in_pl_fit: set[uuid.UUID] = set()
    for order, _wt in weighted_rankings:
        ids_in_pl_fit.update(order)

    cohort_for_pl = sorted(
        (ids_in_pl_fit & cohort_set),
        key=lambda u: str(u),
    )
    not_ranked_ids = sorted(
        (cohort_set - ids_in_pl_fit),
        key=lambda u: str(u),
    )
    logger.info(
        "PL apply: cohort_for_pl=%d not_in_pl_fit=%d ids_in_fit_preview=%s",
        len(cohort_for_pl),
        len(not_ranked_ids),
        [str(u)[:13] + "…" for u in cohort_for_pl[:12]],
    )

    del_res = cast(
        CursorResult[Any],
        db.execute(delete(RankingResult).where(RankingResult.run_id == run_id)),
    )
    logger.info(
        "PL apply: DELETE ranking_results WHERE run_id=%s rowcount=%s",
        run_id,
        del_res.rowcount,
    )

    orch_blob: Dict[str, Any] = dict(run.orchestrator_output) if run.orchestrator_output else {}

    if not cohort_for_pl:
        orch_blob["plackett_luce"] = {
            "global_ranking_candidate_ids": [],
            "utilities": {},
            "cohort_candidate_ids": [str(c) for c in cohort_ids],
            "candidate_ids_ranked_by_plackett_luce": [],
            "candidate_ids_not_ranked_by_plackett_luce": [str(c) for c in not_ranked_ids],
            "fit": {
                "note": "no_mini_tournament_rankings_eligible_for_pl",
                "n_rankings_weighted_in_fit": 0,
            },
            "n_tournaments_in_db": len(tournaments),
        }
        run.orchestrator_output = orch_blob
        logger.warning(
            "PL apply: no PL fit cohort (no eligible rankings) run_id=%s tournaments_in_db=%d not_ranked=%d",
            run_id,
            len(tournaments),
            len(not_ranked_ids),
        )
        return {
            "run_id": str(run_id),
            "plackett_luce": orch_blob["plackett_luce"],
            "plackett_ranked_candidate_ids": [],
        }

    utilities, fit_meta = fit_plackett_luce_utilities(
        cohort_ids=cohort_for_pl,
        weighted_rankings=weighted_rankings,
    )
    logger.info(
        "PL apply: utilities fitted converged=%s n_rankings_used=%s",
        fit_meta.get("converged"),
        fit_meta.get("n_rankings_used"),
    )

    var_by_id = approximate_posterior_variance_heuristic(
        cohort_ids=cohort_for_pl,
        appearances=dict(appearances),
    )

    cohort_sorted = sorted(
        cohort_for_pl,
        key=lambda c: (-utilities.get(str(c), 0.0), str(c)),
    )

    for position, cid in enumerate(cohort_sorted, start=1):
        sid = str(cid)
        n_app = int(appearances.get(sid, 0))
        db.add(
            RankingResult(
                run_id=run_id,
                candidate_id=cid,
                utility=float(utilities.get(sid, 0.0)),
                posterior_variance=float(var_by_id.get(sid, 1.0)),
                rank_position=position,
                tournaments_seen=n_app,
                decision_trace={
                    "stage": "plackett_luce",
                    "utility": float(utilities.get(sid, 0.0)),
                    "appearances_in_tournaments": n_app,
                },
            )
        )
        logger.debug(
            "PL apply: ORM add RankingResult rank=%s candidate=%s utility=%.5f var=%.5f seen=%s",
            position,
            cid,
            float(utilities.get(sid, 0.0)),
            float(var_by_id.get(sid, 1.0)),
            n_app,
        )

    orch_blob["plackett_luce"] = {
        "global_ranking_candidate_ids": [str(c) for c in cohort_sorted],
        "utilities": {k: float(utilities[k]) for k in sorted(utilities.keys())},
        "cohort_candidate_ids": [str(c) for c in cohort_ids],
        "candidate_ids_ranked_by_plackett_luce": [str(c) for c in cohort_sorted],
        "candidate_ids_not_ranked_by_plackett_luce": [str(c) for c in not_ranked_ids],
        "fit": fit_meta,
        "n_tournaments_in_db": len(tournaments),
        "n_rankings_weighted_in_fit": fit_meta.get("n_rankings_used", 0),
    }
    run.orchestrator_output = orch_blob

    logger.info(
        "PL apply: staged %d RankingResult rows + orchestrator_output.plackett_luce "
        "(commit by caller) run_id=%s global_order=%s",
        len(cohort_sorted),
        run_id,
        [str(c) for c in cohort_sorted],
    )

    return {
        "run_id": str(run_id),
        "plackett_luce": orch_blob["plackett_luce"],
        "plackett_ranked_candidate_ids": [str(c) for c in cohort_sorted],
    }
