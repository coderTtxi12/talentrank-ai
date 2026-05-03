"""Shared AsyncOpenAI client for listwise worker (longer timeout than default API routes)."""

from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings
from langsmith.wrappers import wrap_openai

_client: Optional[AsyncOpenAI] = None


def get_listwise_async_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        if not settings.OPENAI_MODEL:
            raise RuntimeError("OPENAI_MODEL is not configured.")
        _client = wrap_openai(
            AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=settings.OPENAI_LISTWISE_TIMEOUT_SECONDS,
            )
        )
    return _client
