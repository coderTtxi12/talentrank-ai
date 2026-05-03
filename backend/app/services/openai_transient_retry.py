"""Async retry helper for flaky OpenAI HTTP calls.

Retries on timeouts, connection errors, rate limits (429), and 5xx responses
using exponential backoff (extra multiplier on rate limits).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

T = TypeVar("T")

_RETRIABLE = (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError)


async def await_with_transient_retry(
    factory: Callable[[], Awaitable[T]],
    *,
    logger: logging.Logger,
    operation: str,
    max_attempts: int,
    base_delay_seconds: float = 1.5,
) -> T:
    """Run ``factory()`` with exponential backoff on retriable API errors."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return await factory()
        except _RETRIABLE as exc:
            last_exc = exc
            if attempt + 1 >= max_attempts:
                raise
            delay = base_delay_seconds * (2**attempt)
            if isinstance(exc, RateLimitError):
                delay *= 2
            logger.warning(
                "%s: OpenAI error (%s/%s) %s; retrying in %.1fs",
                operation,
                attempt + 1,
                max_attempts,
                exc,
                delay,
            )
            await asyncio.sleep(delay)

    assert last_exc is not None
    raise last_exc
