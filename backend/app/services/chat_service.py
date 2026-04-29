"""Chat orchestrator.

Flow per turn:
    1. Load conversation history (Redis -> Postgres fallback).
    2. Pre-load the screening state for this session (Redis -> Postgres
       fallback) so the agent does not have to spend tool calls reading it.
    3. Run the ReAct screening agent (LLM + tools) for one user turn. The
       agent returns a structured JSON envelope (`reasoning`, `reply`, ...).
    4. Persist the new user/assistant turns to Redis AND Postgres in
       parallel using only the `reply` text.
    5. Return the full envelope so the API can surface metadata.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from app.core.logging import get_logger
from app.services import history_repository, llm_client, screening_state

logger = get_logger(__name__)


async def handle_turn(session_id: str, user_message: str) -> Dict[str, Any]:
    history, preloaded_state = await asyncio.gather(
        history_repository.load_history(session_id),
        screening_state.load_state(session_id),
    )
    logger.info(
        "chat: session=%s history_turns=%d preloaded_fields=%d",
        session_id,
        len(history),
        len(preloaded_state),
    )

    envelope = await llm_client.run_agent(
        session_id=session_id,
        user_message=user_message,
        history=history,
        preloaded_state=preloaded_state,
    )
    reply = str(envelope.get("reply", ""))

    await asyncio.gather(
        history_repository.append_redis(session_id, user_message, reply),
        history_repository.append_postgres(session_id, user_message, reply),
    )

    return envelope
