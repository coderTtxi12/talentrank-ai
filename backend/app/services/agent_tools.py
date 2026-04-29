"""Agent tools exposed to the LLM via OpenAI tool-calling.

Tools available to the screening agent:
    - `search_company_info` (RAG over Chroma)

Persistence of captured fields is no longer a tool. The agent emits the
fields and values in its final JSON envelope (`state_updates`) and the
backend applies them deterministically to Redis and PostgreSQL.

`session_id` is bound via closure (`build_tools`) so the model never has to
pass it explicitly.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from app.core.config import settings
from app.core.logging import get_logger
from app.services import vector_store
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
    """Bind `session_id` to the per-session tools.

    Today only `search_company_info` is exposed. `session_id` is kept on the
    signature so we can re-introduce session-bound tools later without
    changing the caller.
    """

    del session_id  # currently unused; reserved for future per-session tools

    return {
        "search_company_info": _search_company_info,
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
