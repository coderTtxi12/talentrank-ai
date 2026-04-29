"""Async Redis client (singleton).

Uses `redis.asyncio` so we can `await` from FastAPI handlers and run Redis
writes concurrently with PostgreSQL writes via `asyncio.gather`.
"""

from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """Return a process-wide async Redis client."""

    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
