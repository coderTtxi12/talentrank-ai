"""Chat orchestrator.

Flow per turn:
    1. Load history (Redis → Postgres fallback).
    2. Call the LLM with `history + user_message`.
    3. Persist the new user/assistant turns to Redis AND Postgres in parallel.
    4. Return the assistant reply once both writes finish.
"""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.services import history_repository, llm_client

logger = get_logger(__name__)


async def handle_turn(session_id: str, user_message: str) -> str:
    history = await history_repository.load_history(session_id)
    logger.info(
        "chat: session=%s history_turns=%d", session_id, len(history)
    )

    reply = await llm_client.chat_complete(history, user_message)

    await asyncio.gather(
        history_repository.append_redis(session_id, user_message, reply),
        history_repository.append_postgres(session_id, user_message, reply),
    )

    return reply
