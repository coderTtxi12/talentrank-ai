"""Listwise + Plackett-Luce ranking worker.

Placeholder worker. The future job here is to take a candidate cohort and
produce a listwise ranking using a Plackett-Luce model (with feature weights
or learnable parameters). For now the worker simply logs that it has started
and waits for a stop signal so the container stays alive and visible in
`docker compose ps`.

Run locally:
    python -m app.workers.listwise_plackett_luce_worker
"""

from __future__ import annotations

import asyncio
import signal

from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)

WORKER_NAME = "listwise-plackett-luce"


async def run() -> None:
    """Idle worker: log on startup and block until SIGINT/SIGTERM."""

    configure_logging()
    logger.info("Starting %s worker", WORKER_NAME)
    logger.info(
        "🏁 [%s] worker iniciado en modo idle; aún sin lógica de ranking implementada",
        WORKER_NAME,
    )

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

    await stop_event.wait()
    logger.info("[%s] worker stopped", WORKER_NAME)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
