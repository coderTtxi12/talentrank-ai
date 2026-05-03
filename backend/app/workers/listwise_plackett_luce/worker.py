"""Listwise ranking worker: LISTEN/NOTIFY on new jobs + orchestrated LLM tournaments.

Wakes on `listwise_job_pending` when a row is inserted into `jobs` with
`job_type = listwise`. Claims work with a single atomic UPDATE so concurrent
workers never process the same job twice.
"""

from __future__ import annotations

import asyncio
import os
import signal
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

import psycopg
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging, get_logger
from app.models.database import Job, JobStatus, JobType
from app.workers.listwise_plackett_luce.cohort import (
    advance_candidates_to_listwise_status,
    list_candidate_ids_pending_listwise,
    read_jd_public_context,
)
from app.workers.listwise_plackett_luce.persistence import (
    persist_listwise_orch_and_tournaments,
)
from app.workers.listwise_plackett_luce.orchestrator import run_listwise_orchestrator

logger = get_logger(__name__)

WORKER_NAME = "listwise-worker"
CHANNEL = "listwise_job_pending"
WORKER_ID = os.environ.get("LISTWISE_WORKER_ID", f"listwise-{os.getpid()}")

_INITIAL_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 30.0


def _psycopg_dsn() -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url[len("postgresql+psycopg://") :]
    return url


def claim_listwise_job_sync(job_id: uuid.UUID, worker_id: str) -> bool:
    """Exactly one worker wins: pending listwise row -> running."""

    with SessionLocal() as db:
        res = cast(
            CursorResult[Any],
            db.execute(
            update(Job)
            .where(
                Job.id == job_id,
                Job.job_type == JobType.LISTWISE,
                Job.status == JobStatus.PENDING,
            )
            .values(
                status=JobStatus.RUNNING,
                locked_at=datetime.now(timezone.utc),
                locked_by=worker_id,
                attempts=Job.attempts + 1,
            )
            ),
        )
        db.commit()
        return (res.rowcount or 0) == 1


def list_pending_listwise_job_ids_sync() -> List[uuid.UUID]:
    with SessionLocal() as db:
        rows = db.execute(
            select(Job.id)
            .where(
                Job.job_type == JobType.LISTWISE,
                Job.status == JobStatus.PENDING,
            )
            .order_by(Job.created_at.asc())
        ).all()
        return [r[0] for r in rows]


def complete_listwise_job_sync(job_id: uuid.UUID, result: Dict[str, Any]) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.DONE
        base: Dict[str, Any] = dict(job.payload) if isinstance(job.payload, dict) else {}
        base["result"] = result
        job.payload = base
        db.commit()


def fail_listwise_job_sync(job_id: uuid.UUID, message: str) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.FAILED
        job.last_error = (message or "")[:8000]
        db.commit()


def _vacancy_id_from_job_payload(payload: Any) -> Optional[uuid.UUID]:
    if not isinstance(payload, dict):
        return None
    raw = payload.get("vacancy_id")
    if raw is None or raw == "":
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


def _finalize_listwise_after_orchestrator_sync(
    job_id: uuid.UUID,
    vacancy_id: Optional[uuid.UUID],
    candidate_ids: List[uuid.UUID],
    orch: Dict[str, Any],
) -> uuid.UUID:
    """Persist ranking rows (orchestrator + tournaments), then advance candidate status."""

    label = (settings.OPENAI_MODEL or "").strip() or "unknown"
    with SessionLocal() as db:
        run_id = persist_listwise_orch_and_tournaments(
            db,
            job_id=job_id,
            vacancy_id=vacancy_id,
            cohort_ids=candidate_ids,
            orch=orch,
            model_label=label,
        )
        advance_candidates_to_listwise_status(db, candidate_ids)
        db.commit()
        return run_id


async def _run_listwise_pipeline(job_id: uuid.UUID) -> Dict[str, Any]:
    """After a successful claim, load cohort, run orchestrator, advance statuses."""

    vacancy_id: Optional[uuid.UUID]
    with SessionLocal() as db:
        row = db.get(Job, job_id)
        if row is None:
            return {"error": "job_missing"}
        vacancy_id = _vacancy_id_from_job_payload(row.payload)
        candidate_ids = list_candidate_ids_pending_listwise(db, vacancy_id=vacancy_id)

    if not candidate_ids:
        return {
            "job_id": str(job_id),
            "vacancy_id": str(vacancy_id) if vacancy_id else None,
            "empty_cohort": True,
            "message": "No candidates in sentiment_analysis for this scope.",
        }

    jd = read_jd_public_context()
    orch = await run_listwise_orchestrator(
        jd_context=jd,
        candidate_ids=[str(c) for c in candidate_ids],
    )

    run_id = await asyncio.to_thread(
        _finalize_listwise_after_orchestrator_sync,
        job_id,
        vacancy_id,
        candidate_ids,
        orch,
    )

    return {
        "job_id": str(job_id),
        "vacancy_id": str(vacancy_id) if vacancy_id else None,
        "cohort_candidate_ids": [str(c) for c in candidate_ids],
        "ranking_run_id": str(run_id),
        "orchestrator": orch,
    }


async def _handle_job_notification(payload: str) -> None:
    raw = (payload or "").strip()
    if not raw:
        logger.warning("[%s] NOTIFY con payload vacío", WORKER_NAME)
        return
    try:
        job_id = uuid.UUID(raw)
    except ValueError:
        logger.warning("[%s] payload UUID inválido: %r", WORKER_NAME, raw)
        return

    claimed = await asyncio.to_thread(claim_listwise_job_sync, job_id, WORKER_ID)
    if not claimed:
        logger.info(
            "[%s] trabajo %s no reclamado (otro worker o no pendiente)",
            WORKER_NAME,
            job_id,
        )
        return

    try:
        result = await _run_listwise_pipeline(job_id)
        await asyncio.to_thread(complete_listwise_job_sync, job_id, result)
        logger.info("[%s] job done job_id=%s", WORKER_NAME, job_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[%s] job failed job_id=%s", WORKER_NAME, job_id)
        await asyncio.to_thread(fail_listwise_job_sync, job_id, str(exc))


async def _drain_pending_before_listen() -> None:
    ids = await asyncio.to_thread(list_pending_listwise_job_ids_sync)
    if not ids:
        return
    logger.info("[%s] drenando %d trabajos pendientes al arrancar", WORKER_NAME, len(ids))
    for jid in ids:
        await _handle_job_notification(str(jid))


async def _listen_loop(stop_event: asyncio.Event) -> None:
    dsn = _psycopg_dsn()
    logger.info("[%s] conectando a Postgres LISTEN %s", WORKER_NAME, CHANNEL)

    async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"LISTEN {CHANNEL};")
        logger.info("[%s] suscrito a canal '%s'", WORKER_NAME, CHANNEL)

        gen = conn.notifies()

        async def _next_notify() -> psycopg.Notify:
            return await gen.__anext__()

        try:
            while not stop_event.is_set():
                notify_task = asyncio.create_task(_next_notify())
                stop_task = asyncio.create_task(stop_event.wait())
                done, pending = await asyncio.wait(
                    {notify_task, stop_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                if stop_task in done:
                    return
                notify = notify_task.result()
                await _handle_job_notification(notify.payload)
        finally:
            await gen.aclose()


async def run() -> None:
    configure_logging()
    logger.info("Starting %s worker_id=%s", WORKER_NAME, WORKER_ID)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop(signame: str) -> None:
        logger.info("[%s] received %s, stopping", WORKER_NAME, signame)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop, sig.name)
        except NotImplementedError:
            pass

    await _drain_pending_before_listen()

    backoff = _INITIAL_BACKOFF_SECONDS
    while not stop_event.is_set():
        try:
            await _listen_loop(stop_event)
            backoff = _INITIAL_BACKOFF_SECONDS
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "[%s] LISTEN loop crashed: %s. Reconnecting in %.1fs",
                WORKER_NAME,
                exc,
                backoff,
            )
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)

    logger.info("[%s] worker stopped", WORKER_NAME)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
