"""Async OpenAI client wrapper.

Reads API key, model and timeout from `Settings` (no hardcoding).
Exposes a single `chat_complete(history, user_message)` method that returns
the assistant reply text.
"""

from __future__ import annotations

from typing import List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        if not settings.OPENAI_MODEL:
            raise RuntimeError("OPENAI_MODEL is not configured.")
        _client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        )
    return _client


async def chat_complete(
    history: List[dict],
    user_message: str,
    *,
    system_prompt: Optional[str] = None,
) -> str:
    """Call the configured chat-completions model and return the reply text.

    `history` is a list of `{"role": "user"|"assistant", "content": "..."}`
    in chronological order. We prepend a system prompt and append the new
    user message before calling the API.
    """

    client = _get_client()
    sys_prompt = system_prompt if system_prompt is not None else settings.OPENAI_SYSTEM_PROMPT

    messages: List[dict] = []
    if sys_prompt:
        messages.append({"role": "system", "content": sys_prompt})
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    logger.debug(
        "LLM call: model=%s history_turns=%d", settings.OPENAI_MODEL, len(history)
    )

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
    )

    reply = (response.choices[0].message.content or "").strip()
    return reply
