"""ReAct-style screening agent using OpenAI tool-calling.

The agent runs a bounded loop:
    user message
        -> LLM responds with text and/or tool calls
        -> we execute the tools and append their outputs as `role=tool`
        -> loop until the LLM produces a plain assistant message (no tool calls)
           or `max_steps` is reached.

Tools available are bound per-session (see `agent_tools.build_tools`) so the
model never has to handle the `session_id` itself.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.services.agent_tools import (
    TOOL_SCHEMAS,
    build_tools,
    call_tool,
)
from prompts.prompts import SCREENING_SYSTEM_PROMPT

logger = get_logger(__name__)

DEFAULT_MAX_STEPS = 6

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


def _assistant_msg_to_dict(msg: Any) -> Dict[str, Any]:
    """Convert an OpenAI assistant message into a plain dict the API will
    accept on the next request. Drops `None` content so it stays valid when
    the model only emits tool calls."""

    out: Dict[str, Any] = {"role": "assistant"}
    if getattr(msg, "content", None) is not None:
        out["content"] = msg.content
    tool_calls = getattr(msg, "tool_calls", None) or []
    if tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ]
    return out


def _parse_arguments(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


async def run_agent(
    *,
    session_id: str,
    user_message: str,
    history: List[Dict[str, str]],
    max_steps: int = DEFAULT_MAX_STEPS,
    system_prompt: Optional[str] = None,
) -> str:
    """Run the screening agent for one user turn and return the final reply.

    `history` is the prior `[{role, content}]` (user/assistant only). The
    system prompt is sourced from `prompts.prompts.SCREENING_SYSTEM_PROMPT`
    by default.
    """

    client = _get_client()
    tools = build_tools(session_id)
    sys_prompt = system_prompt if system_prompt is not None else SCREENING_SYSTEM_PROMPT

    messages: List[Dict[str, Any]] = [{"role": "system", "content": sys_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    final_text = ""

    for step in range(max_steps):
        logger.debug(
            "agent step=%d session=%s msgs=%d",
            step,
            session_id,
            len(messages),
        )
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,  # type: ignore[arg-type]
            tools=TOOL_SCHEMAS,  # type: ignore[arg-type]
            tool_choice="auto",
        )
        msg = response.choices[0].message
        messages.append(_assistant_msg_to_dict(msg))

        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            final_text = (msg.content or "").strip()
            break

        for tc in tool_calls:
            name = tc.function.name
            args = _parse_arguments(tc.function.arguments)
            logger.info(
                "agent tool call: session=%s name=%s args_keys=%s",
                session_id,
                name,
                list(args.keys()),
            )
            result = await call_tool(name, args, tools)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )
    else:
        logger.warning(
            "agent hit max_steps=%d without final reply (session=%s)",
            max_steps,
            session_id,
        )
        final_text = (
            "Lo siento, no pude completar la respuesta en este momento. "
            "¿Podemos continuar?"
        )

    return final_text
