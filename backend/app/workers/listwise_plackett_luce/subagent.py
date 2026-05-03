"""Single-group listwise ranking via a dedicated LLM call (no tools)."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List

from app.core.config import settings
from app.core.logging import get_logger
from app.services.openai_transient_retry import await_with_transient_retry
from app.workers.listwise_plackett_luce.openai_listwise import get_listwise_async_client
from prompts.prompts import LISTWISE_SUBAGENT_SYSTEM_PROMPT

logger = get_logger(__name__)


def _get_client():
    return get_listwise_async_client()


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

    async def _sub_completion():
        return await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": LISTWISE_SUBAGENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )

    response = await await_with_transient_retry(
        _sub_completion,
        logger=logger,
        operation="listwise_subagent_ranking",
        max_attempts=settings.OPENAI_LISTWISE_MAX_RETRIES,
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
