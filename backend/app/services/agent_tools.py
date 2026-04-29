"""Agent tools exposed to the LLM via OpenAI tool-calling.

Tools available to the screening agent:
    - `search_company_info` (RAG over Chroma)
    - `update_screening_state` (write captured fields to Redis)
    - `update_screening_state_db` (write captured fields to Postgres)

`session_id` is bound via closure (`build_tools`) so the model never has to
pass it explicitly and cannot use a tool to read another session's state.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from app.core.config import settings
from app.core.logging import get_logger
from app.services import screening_state, vector_store
from langsmith import traceable

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# JSON schemas (OpenAI tool-calling format)
# ---------------------------------------------------------------------------


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_company_info",
            "description": (
                "Semantic search over Grupo Sazon public knowledge base "
                "(salary, benefits, locations, schedules, requirements, "
                "tools, communication policy). Use it whenever the candidate "
                "asks a factual question about the company or job."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language query to retrieve.",
                    },
                    "k": {
                        "type": "integer",
                        "description": (
                            "Number of chunks to retrieve. Defaults to the "
                            "configured RAG_TOP_K when omitted."
                        ),
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_screening_state",
            "description": (
                "Persist captured fields to Redis for the current session. "
                "Call this immediately after the candidate confirms a value. "
                "Only the listed fields are accepted; unknown fields are "
                "ignored."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "object",
                        "description": "Map of field -> value to persist.",
                        "properties": {
                            "full_name": {"type": "string"},
                            "drivers_license": {"type": "boolean"},
                            "city": {"type": "string"},
                            "language": {
                                "type": "string",
                                "enum": ["es-ES", "es-MX", "en"],
                            },
                            "availability": {
                                "type": "string",
                                "enum": ["full_time", "part_time", "weekends"],
                            },
                            "preferred_schedule": {
                                "type": "string",
                                "enum": [
                                    "morning",
                                    "afternoon",
                                    "evening",
                                    "flexible",
                                ],
                            },
                            "experience_years": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 50,
                            },
                            "platforms": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "start_date": {
                                "type": "string",
                                "description": "ISO date YYYY-MM-DD.",
                            },
                            "consent": {"type": "boolean"},
                        },
                        "additionalProperties": False,
                    }
                },
                "required": ["updates"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_screening_state_db",
            "description": (
                "Persist captured fields to PostgreSQL for the current "
                "session's candidate record. Use this when you need a durable "
                "database update after confirmation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "object",
                        "description": "Map of field -> value to persist.",
                        "properties": {
                            "full_name": {"type": "string"},
                            "drivers_license": {"type": "boolean"},
                            "city": {"type": "string"},
                            "language": {
                                "type": "string",
                                "enum": ["es-ES", "es-MX", "en"],
                            },
                            "availability": {
                                "type": "string",
                                "enum": ["full_time", "part_time", "weekends"],
                            },
                            "preferred_schedule": {
                                "type": "string",
                                "enum": [
                                    "morning",
                                    "afternoon",
                                    "evening",
                                    "flexible",
                                ],
                            },
                            "experience_years": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 50,
                            },
                            "platforms": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "start_date": {
                                "type": "string",
                                "description": "ISO date YYYY-MM-DD.",
                            },
                            "consent": {"type": "boolean"},
                        },
                        "additionalProperties": False,
                    }
                },
                "required": ["updates"],
                "additionalProperties": False,
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


ToolFn = Callable[..., Union[Dict[str, Any], Awaitable[Dict[str, Any]]]]

@traceable
def _search_company_info(query: str, k: Optional[int] = None) -> Dict[str, Any]:
    top_k = k if isinstance(k, int) and k > 0 else settings.RAG_TOP_K
    try:
        hits = vector_store.semantic_search(query, k=top_k)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG search failed: %s", exc)
        return {"error": str(exc), "results": []}
    return {"query": query, "k": top_k, "results": hits}

def build_tools(session_id: str) -> Dict[str, ToolFn]:
    """Bind `session_id` to the per-session tools."""

    async def update_screening_state(updates: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(updates, dict):
            return {"error": "`updates` must be a JSON object"}
        return await screening_state.update_state_redis(session_id, updates)

    async def update_screening_state_db(updates: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(updates, dict):
            return {"error": "`updates` must be a JSON object"}
        return await screening_state.update_state_db(session_id, updates)

    return {
        "search_company_info": _search_company_info,
        "update_screening_state": update_screening_state,
        "update_screening_state_db": update_screening_state_db,
    }

@traceable
async def call_tool(
    name: str, arguments: Dict[str, Any], tools: Dict[str, ToolFn]
) -> Dict[str, Any]:
    fn = tools.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        result = fn(**arguments)
        if asyncio.iscoroutine(result):
            result = await result
        return result if isinstance(result, dict) else {"result": result}
    except TypeError as exc:
        return {"error": f"bad arguments for {name}: {exc}"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("tool %s failed", name)
        return {"error": f"{type(exc).__name__}: {exc}"}
