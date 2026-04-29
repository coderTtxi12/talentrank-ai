"""Screening state repository.

Stores the structured fields the agent captures from the candidate
(full_name, drivers_license, city, language, availability, etc.) keyed by
`session_id`.

Storage:
    - **Redis** (hot path): single JSON blob at `screen:<session_id>` with TTL.
      Read/write happens here from the agent tools.
    - **PostgreSQL** (read-only fallback): joins `conversations` by
      `session_id` to the linked `candidates` row. Used only when Redis has
      no state for the session.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.models.database import Candidate, Conversation

logger = get_logger(__name__)


ALLOWED_FIELDS: List[str] = [
    "full_name",
    "drivers_license",
    "city",
    "language",
    "availability",
    "preferred_schedule",
    "experience_years",
    "platforms",
    "start_date",
    "consent",
]


def _state_key(session_id: str) -> str:
    return f"screen:{session_id}"


def _coerce(field: str, value: Any) -> Any:
    """Lightweight normalization so the agent can pass loose inputs."""

    if value is None:
        return None
    if field in {"drivers_license", "consent"}:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "yes", "y", "si", "sí", "1"}
        return bool(value)
    if field == "experience_years":
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    if field == "platforms":
        if isinstance(value, str):
            return [p.strip() for p in value.split(",") if p.strip()]
        if isinstance(value, list):
            return [str(p).strip() for p in value if str(p).strip()]
        return None
    if field == "start_date" and isinstance(value, date):
        return value.isoformat()
    return value


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------


async def get_state_redis(session_id: str) -> Dict[str, Any]:
    redis = get_redis()
    raw = await redis.get(_state_key(session_id))  # type: ignore[misc]
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Corrupt screening state in redis for %s", session_id)
        return {}


async def update_state_redis(
    session_id: str, updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge `updates` (only ALLOWED_FIELDS) into the per-session state."""

    if not isinstance(updates, dict):
        raise ValueError("updates must be a JSON object")

    redis = get_redis()
    key = _state_key(session_id)
    current = await get_state_redis(session_id)

    applied: Dict[str, Any] = {}
    for field, value in updates.items():
        if field not in ALLOWED_FIELDS:
            continue
        coerced = _coerce(field, value)
        if coerced is None:
            continue
        current[field] = coerced
        applied[field] = coerced

    await redis.set(  # type: ignore[misc]
        key, json.dumps(current, ensure_ascii=False, default=str)
    )
    await redis.expire(key, settings.SESSION_TTL_SECONDS)  # type: ignore[misc]

    return {"applied": applied, "state": current}


# ---------------------------------------------------------------------------
# PostgreSQL (read-only fallback)
# ---------------------------------------------------------------------------


def _read_state_pg_sync(session_id: str) -> Dict[str, Any]:
    with SessionLocal() as db:
        conv = db.scalar(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        if conv is None or conv.candidate_id is None:
            return {}
        candidate: Optional[Candidate] = db.get(Candidate, conv.candidate_id)
        if candidate is None:
            return {}
        out: Dict[str, Any] = {
            "full_name": candidate.full_name,
            "language": candidate.language.value if candidate.language else None,
            "consent": bool(candidate.consent),
            "drivers_license": candidate.drivers_license,
            "availability": (
                candidate.availability.value if candidate.availability else None
            ),
            "preferred_schedule": (
                candidate.preferred_schedule.value
                if candidate.preferred_schedule
                else None
            ),
            "experience_years": candidate.experience_years,
            "platforms": list(candidate.platforms) if candidate.platforms else None,
            "start_date": (
                candidate.start_date.isoformat() if candidate.start_date else None
            ),
        }
        return {k: v for k, v in out.items() if v is not None}


async def get_state_db(session_id: str) -> Dict[str, Any]:
    return await asyncio.to_thread(_read_state_pg_sync, session_id)
