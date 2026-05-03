"""Single-group listwise ranking via a dedicated LLM call (no tools)."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from prompts.prompts import LISTWISE_SUBAGENT_SYSTEM_PROMPT
from langsmith.wrappers import wrap_openai

logger = get_logger(__name__)

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


def _sanitize_order(raw: List[Any], allowed: set[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for x in raw:
        sid = str(x).strip()
        if sid in allowed and sid not in seen:
            out.append(sid)
            seen.add(sid)
    tail = [i for i in sorted(allowed) if i not in seen]
    return out + tail


async def run_group_ranking_subagent(
    *,
    candidate_ids: List[str],
    orchestrator_instructions: str,
    jd_context: str,
    candidate_cards: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Return {ordered_candidate_ids, rationale}."""

    allowed = {str(x).strip() for x in candidate_ids if str(x).strip()}
    if not allowed:
        return {"ordered_candidate_ids": [], "rationale": "empty_group", "error": "empty_group"}

    client = _get_client()
    payload = {
        "jd_context": jd_context[:16000],
        "orchestrator_instructions": orchestrator_instructions[:4000],
        "candidates": {cid: candidate_cards.get(cid, {}) for cid in allowed},
    }
    user_content = (
        "Rank this candidate group per the orchestrator instructions and dossiers below.\n"
        f"<payload>{json.dumps(payload, ensure_ascii=False, default=str)}</payload>"
    )

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": LISTWISE_SUBAGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )
    text = (response.choices[0].message.content or "").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("subagent invalid JSON, falling back to lexical order")
        return {
            "ordered_candidate_ids": sorted(allowed),
            "rationale": "fallback:invalid_json_from_subagent",
            "raw": text[:2000],
        }

    ordered_raw = data.get("ordered_candidate_ids")
    if not isinstance(ordered_raw, list):
        ordered_raw = []
    ordered = _sanitize_order(ordered_raw, allowed)
    rationale = str(data.get("rationale") or "")[:1200]

    return {
        "ordered_candidate_ids": ordered,
        "rationale": rationale,
    }


def validate_uuid_list(ids: List[str]) -> List[str]:
    out: List[str] = []
    for i in ids:
        try:
            out.append(str(uuid.UUID(str(i).strip())))
        except ValueError:
            continue
    return out
