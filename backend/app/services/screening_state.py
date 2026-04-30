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
from app.models.database import (
    Availability,
    Candidate,
    Conversation,
    Language,
    PreferredSchedule,
)

logger = get_logger(__name__)


ALLOWED_FIELDS: List[str] = [
    "full_name",
    "drivers_license",
    "city",
    "city_zone",
    "language",
    "availability",
    "preferred_schedule",
    "experience_years",
    "platforms",
    "start_date",
]


def _state_key(session_id: str) -> str:
    return f"screen:{session_id}"


def _coerce(field: str, value: Any) -> Any:
    """Lightweight normalization so the agent can pass loose inputs."""

    if value is None:
        return None
    if field == "drivers_license":
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


def _enum_or_none(enum_cls: Any, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return None
    return None


def _date_or_none(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


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
            "drivers_license": candidate.drivers_license,
            "city_zone": candidate.city_zone,
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


# ---------------------------------------------------------------------------
# Combined loader (Redis -> Postgres fallback, with cache warm-up)
# ---------------------------------------------------------------------------


async def load_state(session_id: str, *, warm_cache: bool = True) -> Dict[str, Any]:
    """Return the captured screening state for a session.

    Tries Redis first; falls back to PostgreSQL on cache miss. When the
    fallback returns data and ``warm_cache`` is true, the values are written
    back into Redis so the next turn does not pay the DB cost.
    """

    redis_state = await get_state_redis(session_id)
    if redis_state:
        return redis_state

    pg_state = await get_state_db(session_id)
    if pg_state and warm_cache:
        try:
            await update_state_redis(session_id, pg_state)
        except Exception as exc:  # noqa: BLE001
            logger.warning("warm_cache failed for %s: %s", session_id, exc)
    return pg_state


def _update_state_pg_sync(session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with SessionLocal() as db:
        conv = db.scalar(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        if conv is None:
            return {"applied": {}, "state": {}, "warning": "conversation_not_found"}

        candidate: Optional[Candidate] = None
        if conv.candidate_id is not None:
            candidate = db.get(Candidate, conv.candidate_id)
        if candidate is None:
            candidate = Candidate()
            db.add(candidate)
            db.flush()
            conv.candidate_id = candidate.id

        normalized: Dict[str, Any] = {}
        for field, value in updates.items():
            if field not in ALLOWED_FIELDS:
                continue
            coerced = _coerce(field, value)
            if coerced is not None:
                normalized[field] = coerced

        applied: Dict[str, Any] = {}

        if "full_name" in normalized:
            candidate.full_name = str(normalized["full_name"])
            applied["full_name"] = candidate.full_name
        if "drivers_license" in normalized:
            candidate.drivers_license = bool(normalized["drivers_license"])
            applied["drivers_license"] = candidate.drivers_license
        if "language" in normalized:
            lang = _enum_or_none(Language, normalized["language"])
            if lang is not None:
                candidate.language = lang
                applied["language"] = lang.value
        if "availability" in normalized:
            availability = _enum_or_none(Availability, normalized["availability"])
            if availability is not None:
                candidate.availability = availability
                applied["availability"] = availability.value
        if "preferred_schedule" in normalized:
            schedule = _enum_or_none(PreferredSchedule, normalized["preferred_schedule"])
            if schedule is not None:
                candidate.preferred_schedule = schedule
                applied["preferred_schedule"] = schedule.value
        if "experience_years" in normalized:
            candidate.experience_years = int(normalized["experience_years"])
            applied["experience_years"] = candidate.experience_years
        if "platforms" in normalized and isinstance(normalized["platforms"], list):
            candidate.platforms = [str(p) for p in normalized["platforms"]]
            applied["platforms"] = candidate.platforms
        if "start_date" in normalized:
            start = _date_or_none(normalized["start_date"])
            if start is not None:
                candidate.start_date = start
                applied["start_date"] = start.isoformat()
        if "city_zone" in normalized:
            candidate.city_zone = str(normalized["city_zone"])
            applied["city_zone"] = candidate.city_zone
        elif "city" in normalized:
            candidate.city_zone = str(normalized["city"])
            applied["city_zone"] = candidate.city_zone

        db.commit()
        state = _read_state_pg_sync(session_id)
        return {"applied": applied, "state": state}


async def update_state_db(session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(updates, dict):
        raise ValueError("updates must be a JSON object")
    return await asyncio.to_thread(_update_state_pg_sync, session_id, updates)
