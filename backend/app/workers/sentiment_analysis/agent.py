"""LLM-based sentiment analysis for finished screening conversations.

Pure inference helper used by the worker. Knows nothing about Postgres or
LISTEN/NOTIFY: it receives the transcript, calls OpenAI in JSON-only mode and
returns a structured envelope. The worker is responsible for loading the
conversation and persisting the result via SQLAlchemy.

LangSmith: same pattern as ``app.services.llm_client`` — ``wrap_openai`` on the
client plus ``@traceable`` on the async entrypoint (and on the completion
helper so runs nest cleanly). Enable tracing via ``LANGCHAIN_TRACING_V2=true``
(or ``LANGSMITH_TRACING=true``) and ``LANGSMITH_API_KEY`` / ``LANGSMITH_PROJECT``
in the environment (see LangSmith docs).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from prompts.prompts import SENTIMENT_ANALYSIS_SYSTEM_PROMPT
from langsmith import traceable
from langsmith.wrappers import wrap_openai

logger = get_logger(__name__)

_ALLOWED_LABELS = {"positive", "neutral", "confused", "frustrated"}
_ALLOWED_ENGAGEMENT = {"high", "medium", "low"}
_ALLOWED_LICENSE = {"yes", "no", "unknown"}

_KEY_DATA_POINT_FIELDS = (
    "full_name",
    "drivers_license",
    "city_zone",
    "availability",
    "preferred_schedule",
    "experience_years",
    "platforms",
    "start_date",
)

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


def _render_transcript(messages: List[Dict[str, Any]]) -> str:
    """Render ordered turns into a compact transcript for the prompt.

    Only `user` and `assistant` roles are kept. `tool` turns are dropped
    because they are internal noise.
    """

    lines: List[str] = []
    for m in messages:
        role = (m.get("role") or "").lower()
        if role not in {"user", "assistant"}:
            continue
        content = (m.get("content") or "").strip()
        if not content:
            continue
        prefix = "candidate" if role == "user" else "assistant"
        lines.append(f"[{prefix}] {content}")
    return "\n".join(lines)


def _normalize_license_answer(raw: Any) -> str | None:
    """Map model output to canonical yes | no | unknown."""

    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    if s in {"yes", "y", "true", "1", "sí", "si"}:
        return "yes"
    if s in {"no", "n", "false", "0"}:
        return "no"
    if s in {"unknown", "?", "unsure", "na", "n/a"}:
        return "unknown"
    if "no tengo" in s or "sin carnet" in s or "don't have" in s or "dont have" in s:
        return "no"
    if "tengo" in s and ("carnet" in s or "licen" in s):
        return "yes"
    return "unknown"


def _normalize_key_data_points(raw: Any) -> Dict[str, Any]:
    """Keep only Phase-2 screening keys; coerce simple types."""

    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Any] = {}
    for field in _KEY_DATA_POINT_FIELDS:
        if field not in raw:
            continue
        val = raw.get(field)
        if val is None:
            out[field] = None
            continue
        if field == "drivers_license":
            lic = _normalize_license_answer(val)
            out[field] = lic if lic in _ALLOWED_LICENSE else None
            continue
        if field == "experience_years":
            if isinstance(val, bool):
                continue
            if isinstance(val, (int, float)):
                out[field] = float(val)
            elif isinstance(val, str) and val.strip():
                out[field] = val.strip()
            continue
        if field == "platforms":
            if isinstance(val, list):
                plist = [
                    str(x).strip()
                    for x in val
                    if str(x).strip()
                ]
                out[field] = plist if plist else None
            elif isinstance(val, str) and val.strip():
                out[field] = val.strip()
            else:
                out[field] = None
            continue
        if isinstance(val, str):
            trimmed = val.strip()
            out[field] = trimmed if trimmed else None
        elif isinstance(val, (int, float)) and not isinstance(val, bool):
            out[field] = val
        else:
            out[field] = str(val).strip() or None

    return out


def _coerce_envelope(data: Any) -> Dict[str, Any]:
    """Validate and normalize the model output."""

    if not isinstance(data, dict):
        return _fallback_envelope("not_object")

    sentiment = str(data.get("sentiment") or "").strip().lower()
    if sentiment not in _ALLOWED_LABELS:
        sentiment = "neutral"

    raw_conf = data.get("confidence", 0.0)
    try:
        confidence = float(raw_conf)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    raw_signals = data.get("signals")
    signals: Dict[str, Any] = raw_signals if isinstance(raw_signals, dict) else {}

    engagement = str(signals.get("engagement") or "").strip().lower()
    if engagement not in _ALLOWED_ENGAGEMENT:
        engagement = "medium"
    signals["engagement"] = engagement
    signals.setdefault("tone", "")
    signals.setdefault("concerns", [])
    signals.setdefault("evidence", [])
    signals.setdefault("notes", "")

    summary_raw = data.get("post_conversation_summary")
    summary = ""
    if isinstance(summary_raw, str):
        summary = summary_raw.strip()[:4000]

    key_data_points = _normalize_key_data_points(data.get("key_data_points"))

    return {
        "sentiment": sentiment,
        "confidence": confidence,
        "signals": signals,
        "reasoning": str(data.get("reasoning") or "")[:1000],
        "post_conversation_summary": summary,
        "key_data_points": key_data_points,
    }


def _fallback_envelope(reason: str) -> Dict[str, Any]:
    return {
        "sentiment": "neutral",
        "confidence": 0.0,
        "signals": {
            "tone": "",
            "engagement": "medium",
            "concerns": [],
            "evidence": [],
            "notes": f"fallback:{reason}",
        },
        "reasoning": f"fallback:{reason}",
        "post_conversation_summary": "",
        "key_data_points": {},
    }


@traceable
async def _invoke_sentiment_completion(
    messages: List[Dict[str, Any]],
) -> str:
    """Single JSON-mode chat completion; traced as a child run (cf. screening turns)."""

    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,  # type: ignore[arg-type]
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""


@traceable
async def analyze_conversation(
    *,
    candidate_id: str,
    conversation_id: str,
    messages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Run sentiment analysis over a finished conversation transcript.

    Returns the structured envelope per :data:`SENTIMENT_ANALYSIS_SYSTEM_PROMPT`
    (sentiment, confidence, signals, reasoning,
    ``post_conversation_summary``, ``key_data_points``, ``model_version``).
    On any error or empty transcript, a low-confidence neutral fallback is
    returned instead of raising.
    """

    transcript = _render_transcript(messages)
    if not transcript:
        logger.warning(
            "sentiment_agent: empty transcript candidate_id=%s conversation_id=%s",
            candidate_id,
            conversation_id,
        )
        envelope = _fallback_envelope("empty_transcript")
        envelope["model_version"] = settings.OPENAI_MODEL
        return envelope

    user_payload = (
        "Conversation transcript to analyze "
        f"(candidate_id={candidate_id}, conversation_id={conversation_id}):\n"
        "<transcript>\n"
        f"{transcript}\n"
        "</transcript>"
    )

    llm_messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SENTIMENT_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_payload},
    ]

    try:
        raw = await _invoke_sentiment_completion(messages=llm_messages)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "sentiment_agent: invalid JSON from model conversation_id=%s",
                conversation_id,
            )
            envelope = _fallback_envelope("invalid_json")
        else:
            envelope = _coerce_envelope(parsed)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "sentiment_agent: LLM call failed conversation_id=%s: %s",
            conversation_id,
            exc,
        )
        envelope = _fallback_envelope("llm_error")

    envelope["model_version"] = settings.OPENAI_MODEL
    return envelope
