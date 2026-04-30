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
from langsmith import traceable
from langsmith.wrappers import wrap_openai

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
        _client = wrap_openai(
            AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=settings.OPENAI_TIMEOUT_SECONDS,
            )
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

_REQUIRED_JSON_KEYS = {
    "reasoning",
    "reply",
    "language",
    "state_updates",
    "next_action",
    "next_field_to_ask",
    "candidate_status_hint",
    "security_flag",
    "needs_human",
    "confidence",
}


def _fallback_envelope(reply: str, *, reason: str) -> Dict[str, Any]:
    return {
        "reasoning": f"fallback:{reason}",
        "reply": reply,
        "language": "es-MX",
        "state_updates": {},
        "next_action": "ask_field",
        "next_field_to_ask": None,
        "candidate_status_hint": "in_progress",
        "security_flag": "none",
        "needs_human": False,
        "confidence": 0.0,
    }


def _parse_final_json(text: str) -> Dict[str, Any]:
    """Parse the final assistant JSON envelope, with a graceful fallback."""

    if not text:
        return _fallback_envelope("", reason="empty")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _fallback_envelope(text.strip(), reason="invalid_json")
    if not isinstance(data, dict):
        return _fallback_envelope(str(data), reason="not_object")
    missing = _REQUIRED_JSON_KEYS - data.keys()
    if missing:
        data.setdefault("reply", "")
        data.setdefault("reasoning", f"missing_keys:{sorted(missing)}")
    return data


def _preloaded_state_message(state: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """Render the pre-loaded screening state as an extra system message.

    The agent should treat it as ground truth and skip calling the
    `get_screening_state_*` tools unless it has reason to believe it is
    stale.
    """

    payload = state if isinstance(state, dict) else {}
    rendered = json.dumps(payload, ensure_ascii=False, default=str)
    return {
        "role": "system",
        "content": (
            "Pre-loaded screening state for the current session "
            "(Redis with Postgres fallback). Trust this as ground truth: "
            f"<screening_state>{rendered}</screening_state>"
        ),
    }


@traceable
async def run_agent(
    *,
    session_id: str,
    user_message: str,
    history: List[Dict[str, str]],
    max_steps: int = DEFAULT_MAX_STEPS,
    preloaded_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the screening agent for one user turn.

    Returns the structured JSON envelope produced by the model
    (`reasoning`, `reply`, `language`, ...). The user-facing text lives in
    the `reply` field.

    `preloaded_state` is the screening state already fetched by the caller
    (Redis with Postgres fallback). When provided, it is injected as a
    second system message so the agent can skip the initial read tool calls.
    """

    client = _get_client()
    tools = build_tools(session_id)
    sys_prompt = SCREENING_SYSTEM_PROMPT

    messages: List[Dict[str, Any]] = [{"role": "system", "content": sys_prompt}]
    state_msg = _preloaded_state_message(preloaded_state)
    if state_msg is not None:
        messages.append(state_msg)
    messages.extend(history)
    messages.append(
        {
            "role": "user",
            "content": f"<current_user_turn>{user_message}</current_user_turn>",
        }
    )

    final_envelope: Dict[str, Any] = _fallback_envelope("", reason="not_set")

    for step in range(max_steps):
        is_last_step = step == max_steps - 1
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
            tool_choice="none" if is_last_step else "auto",
            response_format={"type": "json_object"},
        )
        msg = response.choices[0].message
        messages.append(_assistant_msg_to_dict(msg))

        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            final_envelope = _parse_final_json(msg.content or "")
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
            result = await call_tool(name, args, tools)  # type: ignore[call-arg]
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
        final_envelope = _fallback_envelope(
            "Lo siento, no pude completar la respuesta en este momento. "
            "¿Podemos continuar?",
            reason="max_steps",
        )

    return final_envelope
