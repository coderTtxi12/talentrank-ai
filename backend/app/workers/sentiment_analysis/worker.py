"""Sentiment analysis worker.

Listens on the Postgres `candidate_completed` channel (populated by the trigger
defined in migration `0002_candidate_completed_notify`). Whenever a candidate
flips `is_completed` to true:

    1. Phase 1 - set `candidates.status = HARD_FILTER`, then hard filters
       (driver's license, coverage city) -> may set `HARD_DISQ` on failure.
    2. Phase 2 - **only when phase 1 passes**: set `status = SENTIMENT_ANALYSIS`,
       run the sentiment-analysis LLM agent over the full conversation transcript
       and upsert the result into `sentiment_results`. Hard-disqualified candidates
       skip this step
       so we don't burn LLM tokens on rejected applications.

Design notes:
    * Uses `psycopg.AsyncConnection` directly for LISTEN/NOTIFY -- needs a
      dedicated connection in autocommit mode and an idle wait loop.
    * Reads/updates via sync SQLAlchemy `SessionLocal` inside
      `asyncio.to_thread` so ORM stays single-threaded per operation.
    * Phase 2 is idempotent: `sentiment_results.conversation_id` is UNIQUE and
      we use INSERT ... ON CONFLICT DO UPDATE.
    * On disconnect / transient error the LISTEN loop reconnects with
      exponential backoff capped at `_MAX_BACKOFF_SECONDS`.

Run locally:
    python -m app.workers.sentiment_analysis.worker
"""

from __future__ import annotations

import asyncio
import signal
import uuid
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging, get_logger
from app.models.database import (
    Candidate,
    CandidateStatus,
    Conversation,
    Message,
    Sentiment,
    SentimentResult,
)
from app.workers.sentiment_analysis.agent import analyze_conversation
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


# ---------------------------------------------------------------------------
# Phase 1: hard filters
# ---------------------------------------------------------------------------


def _phase1_hard_filters_sync(candidate_id: uuid.UUID) -> bool:
    """Apply hard filters.

    Returns True only when the candidate exists, has finished screening AND
    passed every hard requirement. Returning False signals the caller to skip
    downstream phases (sentiment analysis, ranking, ...). Hard-disqualified
    candidates also return False.
    """

    with SessionLocal() as db:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            logger.warning(
                "[%s] phase1: candidato no encontrado candidate_id=%s",
                WORKER_NAME,
                candidate_id,
            )
            return False

        if not candidate.is_completed:
            logger.warning(
                "[%s] phase1: is_completed=false (inesperado tras NOTIFY) candidate_id=%s",
                WORKER_NAME,
                candidate_id,
            )
            return False

        candidate.status = CandidateStatus.HARD_FILTER
        db.commit()
        logger.info(
            "[%s] phase1: status=hard_filter (inicio evaluación) candidate_id=%s",
            WORKER_NAME,
            candidate_id,
        )

        reasons: list[str] = []

        if candidate.drivers_license is None or candidate.drivers_license is False:
            reasons.append("drivers_license_missing_or_false")

        if not city_zone_in_coverage(candidate.city_zone):
            reasons.append("city_zone_out_of_coverage")

        if reasons:
            candidate.status = CandidateStatus.HARD_DISQ
            db.commit()
            logger.info(
                "[%s] phase1: HARD_DISQ candidate_id=%s reasons=%s — phase2 omitida",
                WORKER_NAME,
                candidate_id,
                reasons,
            )
            return False

        logger.info(
            "[%s] phase1: filtros duros OK candidate_id=%s",
            WORKER_NAME,
            candidate_id,
        )
        return True


def _set_candidate_status_sync(candidate_id: uuid.UUID, status: CandidateStatus) -> None:
    """Persist a status transition (used between pipeline phases)."""

    with SessionLocal() as db:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            return
        candidate.status = status
        db.commit()


# ---------------------------------------------------------------------------
# Phase 2: sentiment analysis
# ---------------------------------------------------------------------------


def _load_latest_conversation_sync(
    candidate_id: uuid.UUID,
) -> Optional[Tuple[uuid.UUID, List[Dict[str, Any]]]]:
    """Return `(conversation_id, ordered_messages)` for the candidate.

    Picks the most recent conversation linked to the candidate. Messages are
    returned in chronological order with role + content.
    """

    with SessionLocal() as db:
        conv = db.scalar(
            select(Conversation)
            .where(Conversation.candidate_id == candidate_id)
            .order_by(Conversation.last_seen_at.desc())
            .limit(1)
        )
        if conv is None:
            logger.warning(
                "[%s] phase2: candidate sin conversation candidate_id=%s",
                WORKER_NAME,
                candidate_id,
            )
            return None

        rows = db.execute(
            select(Message.role, Message.content)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        ).all()

        messages: List[Dict[str, Any]] = [
            {"role": r.value if hasattr(r, "value") else str(r), "content": c}
            for r, c in rows
        ]
        return conv.id, messages


def _persist_sentiment_sync(
    *,
    conversation_id: uuid.UUID,
    envelope: Dict[str, Any],
) -> None:
    """Upsert a row in `sentiment_results` keyed by conversation_id."""

    sentiment_label = str(envelope.get("sentiment", "neutral"))
    try:
        sentiment_enum = Sentiment(sentiment_label)
    except ValueError:
        logger.warning(
            "[%s] phase2: sentiment label inválido %r, usando neutral",
            WORKER_NAME,
            sentiment_label,
        )
        sentiment_enum = Sentiment.NEUTRAL

    confidence = float(envelope.get("confidence", 0.0) or 0.0)
    confidence = max(0.0, min(1.0, confidence))
    signals = envelope.get("signals") or {}
    if not isinstance(signals, dict):
        signals = {"raw": signals}
    if envelope.get("reasoning"):
        signals = {**signals, "reasoning": envelope["reasoning"]}
    pcs = envelope.get("post_conversation_summary")
    if isinstance(pcs, str) and pcs.strip():
        signals = {**signals, "post_conversation_summary": pcs.strip()}
    kdp = envelope.get("key_data_points")
    if isinstance(kdp, dict) and kdp:
        signals = {**signals, "key_data_points": kdp}

    model_version = str(envelope.get("model_version") or settings.OPENAI_MODEL or "unknown")

    stmt = pg_insert(SentimentResult).values(
        conversation_id=conversation_id,
        sentiment=sentiment_enum.value,
        confidence=confidence,
        signals=signals,
        model_version=model_version,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[SentimentResult.conversation_id],
        set_={
            "sentiment": stmt.excluded.sentiment,
            "confidence": stmt.excluded.confidence,
            "signals": stmt.excluded.signals,
            "model_version": stmt.excluded.model_version,
        },
    )

    with SessionLocal() as db:
        db.execute(stmt)
        db.commit()


async def _phase2_sentiment_analysis(candidate_id: uuid.UUID) -> None:
    """Run the sentiment LLM agent and persist the result."""

    await asyncio.to_thread(
        _set_candidate_status_sync,
        candidate_id,
        CandidateStatus.SENTIMENT_ANALYSIS,
    )
    logger.info(
        "[%s] phase2: status=sentiment_analysis candidate_id=%s",
        WORKER_NAME,
        candidate_id,
    )

    loaded = await asyncio.to_thread(_load_latest_conversation_sync, candidate_id)
    if loaded is None:
        return
    conversation_id, messages = loaded
    if not messages:
        logger.warning(
            "[%s] phase2: conversation sin mensajes candidate_id=%s conv=%s",
            WORKER_NAME,
            candidate_id,
            conversation_id,
        )
        return

    logger.info(
        "[%s] phase2: lanzando agente candidate_id=%s conv=%s msgs=%d",
        WORKER_NAME,
        candidate_id,
        conversation_id,
        len(messages),
    )
    envelope = await analyze_conversation(
        candidate_id=str(candidate_id),
        conversation_id=str(conversation_id),
        messages=messages,
    )
    await asyncio.to_thread(
        _persist_sentiment_sync,
        conversation_id=conversation_id,
        envelope=envelope,
    )
    logger.info(
        "[%s] phase2: sentiment guardado candidate_id=%s conv=%s sentiment=%s confidence=%.2f",
        WORKER_NAME,
        candidate_id,
        conversation_id,
        envelope.get("sentiment"),
        float(envelope.get("confidence", 0.0) or 0.0),
    )


# ---------------------------------------------------------------------------
# NOTIFY plumbing
# ---------------------------------------------------------------------------


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

    passed_hard_filters = await asyncio.to_thread(
        _phase1_hard_filters_sync, candidate_id
    )
    if not passed_hard_filters:
        # Candidato no encontrado, sin screening completo, o quedó HARD_DISQ:
        # no gastamos LLM en sentiment analysis.
        return

    try:
        await _phase2_sentiment_analysis(candidate_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "[%s] phase2 falló candidate_id=%s: %s",
            WORKER_NAME,
            candidate_id,
            exc,
        )


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
