"""Sentiment analysis worker.

Listens on the Postgres `candidate_completed` channel (populated by the trigger
defined in migration `0002_candidate_completed_notify`). Whenever a candidate
flips `is_completed` to true, phase 1 applies hard filters (ORM), then future
sentiment logic can run here.

Design notes:
    * Uses `psycopg.AsyncConnection` directly for LISTEN/NOTIFY — needs a
      dedicated connection in autocommit mode and an idle wait loop.
    * Reads and updates screening rows via sync SQLAlchemy `SessionLocal`
      inside `asyncio.to_thread` so ORM stays single-threaded per operation.
    * On disconnect / transient error the loop reconnects with exponential
      backoff capped at `_MAX_BACKOFF_SECONDS`.

Run locally:
    python -m app.workers.sentiment_analysis.worker
"""

from __future__ import annotations

import asyncio
import signal
import uuid

import psycopg

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging, get_logger
from app.models.database import Candidate, CandidateStatus
from app.workers.sentiment_analysis.grupo_sazon_coverage_cities import (
    city_zone_in_coverage,
)

logger = get_logger(__name__)

WORKER_NAME = "sentiment-analysis"
CHANNEL = "candidate_completed"

_INITIAL_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 30.0


def _psycopg_dsn() -> str:
    """Convert the SQLAlchemy URL to a libpq-compatible DSN.

    SQLAlchemy uses `postgresql+psycopg://...`; psycopg expects
    `postgresql://...`.
    """

    url = settings.DATABASE_URL
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url[len("postgresql+psycopg://") :]
    return url


def _phase1_hard_filters_sync(candidate_id: uuid.UUID) -> None:
    """Si el screening está completo, aplicar descalificación dura por licencia o ciudad."""

    with SessionLocal() as db:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            logger.warning(
                "[%s] phase1: candidato no encontrado candidate_id=%s",
                WORKER_NAME,
                candidate_id,
            )
            return

        if not candidate.is_completed:
            logger.warning(
                "[%s] phase1: is_completed=false (inesperado tras NOTIFY) candidate_id=%s",
                WORKER_NAME,
                candidate_id,
            )
            return

        reasons: list[str] = []

        if candidate.drivers_license is None or candidate.drivers_license is False:
            reasons.append("drivers_license_missing_or_false")

        if not city_zone_in_coverage(candidate.city_zone):
            reasons.append("city_zone_out_of_coverage")

        if reasons:
            candidate.status = CandidateStatus.HARD_DISQ
            db.commit()
            logger.info(
                "[%s] phase1: HARD_DISQ candidate_id=%s reasons=%s",
                WORKER_NAME,
                candidate_id,
                reasons,
            )
        else:
            logger.info(
                "[%s] phase1: filtros duros OK candidate_id=%s",
                WORKER_NAME,
                candidate_id,
            )


async def _handle_notification(payload: str) -> None:
    """Acciones cuando un candidato marca screening completado."""

    raw = (payload or "").strip()
    if not raw:
        logger.warning("[%s] NOTIFY con payload vacío", WORKER_NAME)
        return

    try:
        candidate_id = uuid.UUID(raw)
    except ValueError:
        logger.warning("[%s] payload UUID inválido: %r", WORKER_NAME, raw)
        return

    await asyncio.to_thread(_phase1_hard_filters_sync, candidate_id)


async def _listen_loop(stop_event: asyncio.Event) -> None:
    """Single LISTEN session. Returns on disconnect or stop."""

    dsn = _psycopg_dsn()
    logger.info("[%s] connecting to Postgres for LISTEN %s", WORKER_NAME, CHANNEL)

    async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"LISTEN {CHANNEL};")
        logger.info("[%s] subscribed to channel '%s'", WORKER_NAME, CHANNEL)

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
                await _handle_notification(notify.payload)
        finally:
            await gen.aclose()


async def run() -> None:
    """Main worker entrypoint with reconnect/backoff supervision."""

    configure_logging()
    logger.info("Starting %s worker", WORKER_NAME)

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
