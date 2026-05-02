"""Chat orchestrator.

Flow per turn:
    1. Load conversation history (Redis -> Postgres fallback) and the
       pre-loaded screening state for this session, in parallel.
    2. Run the screening agent (LLM + RAG tool) for one user turn. The
       agent returns a structured JSON envelope (`reasoning`, `reply`,
       `state_updates`, ...).
    3. Apply `state_updates` to Redis AND Postgres in parallel (only if
       non-empty).
    4. Persist the new user/assistant turns to Redis AND Postgres in
       parallel using only the `reply` text.
    5. Return the full envelope so the API can surface metadata.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from app.core.logging import get_logger
from app.realtime import broadcast as realtime_broadcast
from app.services import history_repository, llm_client, screening_state

logger = get_logger(__name__)


def _coerce_state_updates(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _coerce_candidate_status_hint(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def _coerce_is_completed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


async def _persist_state_updates(
    session_id: str,
    updates: Dict[str, Any],
    candidate_status_hint: str,
    is_completed: bool,
) -> None:
    if not updates and not candidate_status_hint and not is_completed:
        return
    redis_task = screening_state.update_state_redis(session_id, updates)
    db_task = screening_state.update_state_db(
        session_id,
        updates,
        candidate_status_hint=candidate_status_hint,
        is_completed=is_completed,
    )
    results = await asyncio.gather(redis_task, db_task, return_exceptions=True)
    for label, result in zip(("redis", "postgres"), results):
        if isinstance(result, Exception):
            logger.warning(
                "screening state update failed (%s) for session=%s: %s",
                label,
                session_id,
                result,
            )
        elif label == "postgres" and isinstance(result, dict):
            bc = result.get("status_broadcast")
            if isinstance(bc, dict) and bc.get("candidate_id"):
                await realtime_broadcast.emit_candidate_status_changed(
                    str(bc["candidate_id"]),
                    old_status=str(bc["old_status"]),
                    new_status=str(bc["new_status"]),
                )


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

    state_updates = _coerce_state_updates(envelope.get("state_updates"))
    candidate_status_hint = _coerce_candidate_status_hint(
        envelope.get("candidate_status_hint")
    )
    is_completed = _coerce_is_completed(envelope.get("is_completed"))

    await asyncio.gather(
        _persist_state_updates(
            session_id, state_updates, candidate_status_hint, is_completed
        ),
        history_repository.append_redis(session_id, user_message, reply),
        history_repository.append_postgres(session_id, user_message, reply),
    )

    return envelope
