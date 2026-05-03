"""Persist listwise orchestrator + sub-agent outputs into normalized ranking tables.

Writes:
  * ``ranking_runs`` — one row per job execution (orchestrator summary in JSONB).
  * ``ranking_tournaments`` — one row per sub-agent / tool call (ordering + trace).

Does **not** write ``ranking_results`` (Plackett–Luce not implemented yet).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.database import JobStatus, RankingRun, RankingTournament
from app.workers.listwise_plackett_luce.subagent import validate_uuid_list

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

    pool_n = len(cohort_ids)
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

    for entry in orch.get("tournaments") or []:
        raw_cids = entry.get("candidate_ids") or []
        if not isinstance(raw_cids, list):
            raw_cids = []
        pool = _uuid_list(raw_cids)
        if not pool:
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

    return run.id
