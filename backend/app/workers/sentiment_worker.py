"""Sentiment analysis worker.

Listens on the Postgres `candidate_completed` channel (populated by the trigger
defined in migration `0002_candidate_completed_notify`). Whenever a candidate
flips `is_completed` to true, the worker logs that it has been activated. Real
sentiment analysis logic will be plugged in here later.

Design notes:
    * Uses `psycopg.AsyncConnection` directly, NOT SQLAlchemy. LISTEN/NOTIFY
      requires a dedicated connection in autocommit mode and an idle wait
      loop, which doesn't fit the SQLAlchemy session pattern.
    * Holds a single idle connection per worker process. No polling.
    * On disconnect / transient error the loop reconnects with exponential
      backoff capped at `_MAX_BACKOFF_SECONDS`.
"""

from __future__ import annotations

import asyncio
import signal
from typing import Optional

import psycopg

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)

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


async def _handle_notification(payload: str) -> None:
    """Placeholder action triggered when a candidate completes screening."""

    logger.info(
        "📬 Sentiment worker: he entrado en acción para candidate_id=%s",
        payload or "<empty>",
    )


async def _listen_loop(stop_event: asyncio.Event) -> None:
    """Single LISTEN session. Returns on disconnect or stop."""

    dsn = _psycopg_dsn()
    logger.info("Sentiment worker connecting to Postgres for LISTEN %s", CHANNEL)

    async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"LISTEN {CHANNEL};")
        logger.info("Sentiment worker subscribed to channel '%s'", CHANNEL)

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
    logger.info("Starting sentiment worker")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop(signame: str) -> None:
        logger.info("Received %s, stopping sentiment worker", signame)
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
                "Sentiment worker LISTEN loop crashed: %s. Reconnecting in %.1fs",
                exc,
                backoff,
            )
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)

    logger.info("Sentiment worker stopped")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
