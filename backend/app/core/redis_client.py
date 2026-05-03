"""Async Redis client (lazy singleton).

`get_redis()` builds one `redis.asyncio` client per process on first use so
FastAPI handlers can `await` cache reads/writes. Call `close_redis()` on
application shutdown to release connections cleanly.

Session state and transcript history TTLs are configured via `Settings`
(`SESSION_TTL_SECONDS`, `HISTORY_*`).
"""

from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """Lazily create and return the shared async Redis connection pool."""

    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _client


async def close_redis() -> None:
    """Close and reset the singleton client (e.g. from FastAPI lifespan shutdown)."""

    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
