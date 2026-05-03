"""Integration checks for listwise persistence + Plackett–Luce → ``ranking_results``.

Requires PostgreSQL (same schema as production / alembic). Skips if ``DATABASE_URL``
is unreachable. Uses one transaction and rolls back so the DB stays clean.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

pytest.importorskip("psycopg")

from app.core.database import engine
from app.models.database import Candidate, CandidateStatus, RankingResult
from app.workers.listwise_plackett_luce.persistence import (
    apply_plackett_luce_for_run,
    persist_listwise_orch_and_tournaments,
)


def _pg_ok() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture
def db_conn_session():
    """Connection-bound session; caller rolls back outer transaction."""

    if not _pg_ok():
        pytest.skip("PostgreSQL not reachable (check DATABASE_URL)")
    conn = engine.connect()
    trans = conn.begin()
    sess = Session(bind=conn)
    try:
        yield sess
    finally:
        sess.close()
        trans.rollback()
        conn.close()


def _minimal_candidates(sess: Session, ids: List[uuid.UUID]) -> None:
    for cid in ids:
        sess.add(
            Candidate(
                id=cid,
                full_name=f"PL test {cid.hex[:8]}",
                status=CandidateStatus.SENTIMENT_ANALYSIS,
            )
        )
    sess.flush()


def _fake_orch_two_candidates(c1: uuid.UUID, c2: uuid.UUID) -> Dict[str, Any]:
    """One eligible mini-tournament (confidence 1, ≥2 IDs, not skipped)."""

    return {
        "final_summary": "test",
        "tournaments": [
            {
                "candidate_ids": [str(c1), str(c2)],
                "instructions": "unit test ordering",
                "result": {
                    "ordered_candidate_ids": [str(c2), str(c1)],
                    "rationale": "test",
                },
            }
        ],
    }


@pytest.mark.integration
def test_plackett_luce_writes_ranking_results(db_conn_session: Session) -> None:
    sess = db_conn_session
    c1, c2 = uuid.uuid4(), uuid.uuid4()
    _minimal_candidates(sess, [c1, c2])

    job_id = uuid.uuid4()
    orch = _fake_orch_two_candidates(c1, c2)
    run_id = persist_listwise_orch_and_tournaments(
        sess,
        job_id=job_id,
        vacancy_id=None,
        cohort_ids=[c1, c2],
        orch=orch,
        model_label="test-model",
    )
    pl = apply_plackett_luce_for_run(sess, run_id=run_id, cohort_ids=[c1, c2])
    sess.flush()

    assert pl.get("plackett_ranked_candidate_ids"), "expected ranked ids from PL"
    n = sess.scalar(
        select(func.count()).select_from(RankingResult).where(RankingResult.run_id == run_id)
    )
    assert int(n or 0) == 2


@pytest.mark.integration
def test_two_persist_cycles_two_run_ids_and_ranking_result_rows(db_conn_session: Session) -> None:
    """Each listwise finalize creates a new ``RankingRun``; PL rows are per-run."""

    sess = db_conn_session
    c1, c2 = uuid.uuid4(), uuid.uuid4()
    _minimal_candidates(sess, [c1, c2])
    orch = _fake_orch_two_candidates(c1, c2)

    run_a = persist_listwise_orch_and_tournaments(
        sess,
        job_id=uuid.uuid4(),
        vacancy_id=None,
        cohort_ids=[c1, c2],
        orch=orch,
        model_label="test-model",
    )
    apply_plackett_luce_for_run(sess, run_id=run_a, cohort_ids=[c1, c2])

    run_b = persist_listwise_orch_and_tournaments(
        sess,
        job_id=uuid.uuid4(),
        vacancy_id=None,
        cohort_ids=[c1, c2],
        orch=orch,
        model_label="test-model",
    )
    apply_plackett_luce_for_run(sess, run_id=run_b, cohort_ids=[c1, c2])
    sess.flush()

    assert run_a != run_b
    na = sess.scalar(
        select(func.count()).select_from(RankingResult).where(RankingResult.run_id == run_a)
    )
    nb = sess.scalar(
        select(func.count()).select_from(RankingResult).where(RankingResult.run_id == run_b)
    )
    assert int(na or 0) == 2
    assert int(nb or 0) == 2
