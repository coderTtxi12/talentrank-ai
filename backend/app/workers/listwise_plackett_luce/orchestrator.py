"""Orchestrator LLM with tool calls into ranking subagents (parallel per turn)."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import Counter
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.workers.listwise_plackett_luce.cohort import load_ranking_cards_for_ids
from app.workers.listwise_plackett_luce.subagent import (
    run_group_ranking_subagent,
    validate_uuid_list,
)
from prompts.prompts import LISTWISE_ORCHESTRATOR_SYSTEM_PROMPT
from langsmith.wrappers import wrap_openai

logger = get_logger(__name__)

DEFAULT_MAX_STEPS = 24

_client: Optional[AsyncOpenAI] = None

LISTWISE_ORCHESTRATOR_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "run_group_ranking",
            "description": (
                "Runs one mini-tournament: the sub-agent ranks this candidate subset "
                "from best to worst fit for the Grupo Sazón role."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Candidate UUID strings in this mini-tournament.",
                    },
                    "instructions": {
                        "type": "string",
                        "description": (
                            "Ranking prompt **specific to this sub-agent call**: what to prioritize, "
                            "tie-break rules, and tournament nuance (each call may use different text)."
                        ),
                    },
                },
                "required": ["candidate_ids", "instructions"],
            },
        },
    }
]


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


def _roster_lines(candidate_ids: List[str]) -> str:
    return "\n".join(f"- {cid}" for cid in sorted(set(candidate_ids)))


def _coverage_report(
    tournament_log: List[Dict[str, Any]],
    all_ids: List[str],
) -> Dict[str, Any]:
    cnt: Counter[str] = Counter()
    for entry in tournament_log:
        for cid in entry.get("candidate_ids") or []:
            cnt[str(cid)] += 1
    per = {cid: cnt.get(cid, 0) for cid in all_ids}
    missing = [cid for cid, n in per.items() if n < 3]
    return {
        "appearances_by_candidate": per,
        "min_appearances": min(per.values()) if per else 0,
        "candidates_below_three_tournaments": missing,
        "rule_satisfied": len(missing) == 0,
    }


async def run_listwise_orchestrator(
    *,
    jd_context: str,
    candidate_ids: List[str],
    max_steps: int = DEFAULT_MAX_STEPS,
) -> Dict[str, Any]:
    """Orchestrator: only JD + ID list in model context; each tool loads dossiers via ORM."""

    all_ids = sorted(set(validate_uuid_list([str(x) for x in candidate_ids])))
    if not all_ids:
        return {
            "final_summary": "",
            "tournaments": [],
            "coverage": {
                "appearances_by_candidate": {},
                "min_appearances": 0,
                "candidates_below_three_tournaments": [],
                "rule_satisfied": True,
            },
            "orch_steps_used": 0,
            "error": "empty_cohort_ids",
        }

    allowed_set = set(all_ids)
    client = _get_client()
    tournament_log: List[Dict[str, Any]] = []

    roster = _roster_lines(all_ids)
    sys_extra = (
        f"N={len(all_ids)} candidates. You only know their UUIDs (list below) and the user JD. "
        "You do not receive transcripts or dossiers: each `run_group_ranking` call loads from "
        "the database (ORM) the conversation, sentiment, post-conversation summary, key_data_points, "
        "and remaining candidate fields, and passes them to the sub-agent together with your "
        "`instructions` and the JD.\n"
        "Valid IDs for this run:\n"
        f"{roster}"
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": LISTWISE_ORCHESTRATOR_SYSTEM_PROMPT},
        {"role": "system", "content": sys_extra},
        {
            "role": "user",
            "content": (
                f"<jd_context>\n{jd_context[:20000]}\n</jd_context>\n"
                "<candidate_ids>\n"
                f"{roster}\n"
                "</candidate_ids>"
            ),
        },
    ]

    final_text = ""
    steps_used = 0

    for step in range(max_steps):
        steps_used = step + 1
        is_last = step == max_steps - 1
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,  # type: ignore[arg-type]
            tools=LISTWISE_ORCHESTRATOR_TOOLS,  # type: ignore[arg-type]
            tool_choice="none" if is_last else "auto",
        )
        msg = response.choices[0].message
        messages.append(_assistant_msg_to_dict(msg))
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            final_text = (msg.content or "").strip()
            break

        async def _one_tool(tc: Any) -> Dict[str, str]:
            name = tc.function.name
            args = _parse_arguments(tc.function.arguments)
            if name != "run_group_ranking":
                return {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"error": f"unknown_tool:{name}"}),
                }

            raw_ids = args.get("candidate_ids") or []
            if not isinstance(raw_ids, list):
                raw_ids = []
            cids = validate_uuid_list([str(x) for x in raw_ids])
            instructions = str(args.get("instructions") or "").strip()
            unknown = [c for c in cids if c not in allowed_set]

            if unknown or len(cids) < 1:
                payload = {
                    "error": "invalid_or_empty_group",
                    "unknown": unknown,
                    "candidate_ids": cids,
                    "skipped": True,
                }
                tournament_log.append(
                    {
                        "candidate_ids": cids,
                        "instructions": instructions,
                        "result": payload,
                    }
                )
                return {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(payload, ensure_ascii=False),
                }

            uuid_list = [uuid.UUID(c) for c in cids]
            candidate_cards = await asyncio.to_thread(
                load_ranking_cards_for_ids, uuid_list
            )

            sub = await run_group_ranking_subagent(
                candidate_ids=cids,
                orchestrator_instructions=instructions,
                jd_context=jd_context,
                candidate_cards=candidate_cards,
            )
            tournament_log.append(
                {
                    "candidate_ids": cids,
                    "instructions": instructions,
                    "result": sub,
                }
            )
            return {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(sub, ensure_ascii=False),
            }

        tool_results = await asyncio.gather(*[_one_tool(tc) for tc in tool_calls])
        for tr in tool_results:
            messages.append(tr)  # type: ignore[arg-type]

    coverage = _coverage_report(tournament_log, all_ids)
    return {
        "final_summary": final_text,
        "tournaments": tournament_log,
        "coverage": coverage,
        "orch_steps_used": steps_used,
    }
