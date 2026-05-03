"""Conversation history repository.

Read path:
    1. Try Redis list `hist:<session_id>`.
    2. On miss, fall back to PostgreSQL `conversations` + `messages`.
       Rebuild the Redis list to warm the cache.

Write path:
    Append the just-finished user/assistant turns to BOTH Redis and Postgres.
    The chat_service runs both writes concurrently with `asyncio.gather`.
"""

from __future__ import annotations

import asyncio
import json
from typing import List

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.models.database import Conversation, Message, MessageRole

logger = get_logger(__name__)


def _hist_key(session_id: str) -> str:
    return f"hist:{session_id}"


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


async def load_history(session_id: str) -> List[dict]:
    """Return chat history as a list of `{role, content}` in chronological order.

    Redis first; falls back to Postgres on cache miss and rebuilds the cache.
    Only `user` and `assistant` roles are returned (system prompt is added by
    the LLM client).
    """

    redis = get_redis()
    raw = await redis.lrange(_hist_key(session_id), 0, -1)  # type: ignore[misc]
    if raw:
        return [json.loads(item) for item in raw]

    pg_history = await asyncio.to_thread(_load_history_pg, session_id)
    if pg_history:
        await _warm_cache(session_id, pg_history)
    return pg_history


def _load_history_pg(session_id: str) -> List[dict]:
    """Sync DB read used inside `asyncio.to_thread`."""

    with SessionLocal() as db:
        conv = db.scalar(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        if conv is None:
            return []
        rows = db.scalars(
            select(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.role.in_([MessageRole.USER, MessageRole.ASSISTANT]),
            )
            .order_by(Message.created_at.asc(), Message.id.asc())
            .limit(settings.HISTORY_MAX_TURNS)
        ).all()
        return [{"role": m.role.value, "content": m.content} for m in rows]


async def _warm_cache(session_id: str, history: List[dict]) -> None:
    """Rebuild Redis ``hist:`` list from Postgres-derived turns and set TTL."""

    redis = get_redis()
    key = _hist_key(session_id)
    await redis.delete(key)  # type: ignore[misc]
    for entry in history:
        await redis.rpush(key, json.dumps(entry))  # type: ignore[misc]
    await redis.expire(key, settings.HISTORY_TTL_SECONDS)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Write — Redis
# ---------------------------------------------------------------------------


async def append_redis(
    session_id: str, user_message: str, assistant_message: str
) -> None:
    """Append the latest user+assistant pair to Redis, trim to ``HISTORY_MAX_TURNS``, refresh TTL."""

    redis = get_redis()
    key = _hist_key(session_id)
    await redis.rpush(key, json.dumps({"role": "user", "content": user_message}))  # type: ignore[misc]
    await redis.rpush(
        key, json.dumps({"role": "assistant", "content": assistant_message})
    )  # type: ignore[misc]
    await redis.ltrim(key, -settings.HISTORY_MAX_TURNS, -1)  # type: ignore[misc]
    await redis.expire(key, settings.HISTORY_TTL_SECONDS)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Write — Postgres (sync, wrapped in to_thread by caller)
# ---------------------------------------------------------------------------


def _append_pg_sync(
    session_id: str, user_message: str, assistant_message: str
) -> None:
    with SessionLocal() as db:
        conv = db.scalar(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        if conv is None:
            conv = Conversation(session_id=session_id)
            db.add(conv)
            db.flush()

        db.add_all(
            [
                Message(
                    conversation_id=conv.id,
                    role=MessageRole.USER,
                    content=user_message,
                ),
                Message(
                    conversation_id=conv.id,
                    role=MessageRole.ASSISTANT,
                    content=assistant_message,
                ),
            ]
        )
        db.commit()


async def append_postgres(
    session_id: str, user_message: str, assistant_message: str
) -> None:
    """Persist the same turn pair to ``messages`` (creates ``Conversation`` if needed)."""

    await asyncio.to_thread(
        _append_pg_sync, session_id, user_message, assistant_message
    )
