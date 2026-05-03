"""Load candidate cohorts and rich profiles for listwise ranking."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import (
    Candidate,
    CandidateStatus,
    Conversation,
    Message,
    MessageRole,
    SentimentResult,
)

BACKEND_ROOT = Path(__file__).resolve().parents[3]
JD_PUBLIC_INFO_PATH = BACKEND_ROOT / "docs" / "GRUPO_SAZON_PUBLIC_INFO_ES.txt"


def read_jd_public_context(max_chars: int = 12000) -> str:
    """Plain-text JD / employer context for listwise prompts."""

    if not JD_PUBLIC_INFO_PATH.is_file():
        return ""
    text = JD_PUBLIC_INFO_PATH.read_text(encoding="utf-8", errors="replace")
    return text[:max_chars]


def list_candidate_ids_pending_listwise(
    db: Session,
    *,
    vacancy_id: Optional[uuid.UUID],
) -> List[uuid.UUID]:
    """Candidates that finished sentiment analysis but are not yet in listwise stage."""

    stmt = (
        select(Candidate.id)
        .join(Conversation, Conversation.candidate_id == Candidate.id)
        .where(Candidate.status == CandidateStatus.SENTIMENT_ANALYSIS)
        .distinct()
    )
    if vacancy_id is not None:
        stmt = stmt.where(Conversation.vacancy_id == vacancy_id)
    rows = db.execute(stmt).all()
    return [r[0] for r in rows]


def _latest_conversation_for_candidate(
    db: Session, candidate_id: uuid.UUID
) -> Optional[Conversation]:
    return db.scalar(
        select(Conversation)
        .where(Conversation.candidate_id == candidate_id)
        .order_by(Conversation.last_seen_at.desc())
        .limit(1)
    )


def _render_transcript(
    messages: List[Tuple[MessageRole, str]],
    *,
    max_messages: int = 80,
    max_chars: int = 12000,
) -> str:
    lines: List[str] = []
    total = 0
    slice_msgs = messages[-max_messages:] if len(messages) > max_messages else messages
    for role, content in slice_msgs:
        label = role.value if hasattr(role, "value") else str(role)
        line = f"{label}: {content.strip()}"
        if total + len(line) > max_chars:
            lines.append("…[transcripción truncada]")
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)


def build_candidate_ranking_card(db: Session, candidate_id: uuid.UUID) -> Dict[str, Any]:
    """Single-candidate bundle for orchestrator + subagents."""

    cand = db.get(Candidate, candidate_id)
    if cand is None:
        return {"id": str(candidate_id), "error": "candidate_not_found"}

    conv = _latest_conversation_for_candidate(db, candidate_id)
    transcript = ""
    sentiment_block: Dict[str, Any] = {}
    post_summary = ""
    key_points: Any = {}
    if conv is not None:
        rows = db.execute(
            select(Message.role, Message.content)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        ).all()
        transcript = _render_transcript([(r, c) for r, c in rows])

        sr = db.scalar(
            select(SentimentResult).where(SentimentResult.conversation_id == conv.id)
        )
        if sr is not None:
            sentiment_block = {
                "label": sr.sentiment.value if hasattr(sr.sentiment, "value") else str(sr.sentiment),
                "confidence": float(sr.confidence),
                "signals": sr.signals or {},
            }
            sig = sr.signals if isinstance(sr.signals, dict) else {}
            pcs = sig.get("post_conversation_summary")
            post_summary = pcs.strip() if isinstance(pcs, str) else ""
            kdp = sig.get("key_data_points")
            key_points = kdp if isinstance(kdp, dict) else {}

    return {
        "id": str(candidate_id),
        "full_name": cand.full_name,
        "language": cand.language.value if hasattr(cand.language, "value") else str(cand.language),
        "drivers_license": cand.drivers_license,
        "city_zone": cand.city_zone,
        "availability": cand.availability.value if cand.availability else None,
        "preferred_schedule": cand.preferred_schedule.value if cand.preferred_schedule else None,
        "experience_years": cand.experience_years,
        "platforms": cand.platforms,
        "start_date": cand.start_date.isoformat() if cand.start_date is not None else None,
        "status": cand.status.value if hasattr(cand.status, "value") else str(cand.status),
        "slot_uncertain": cand.slot_uncertain,
        "conversation_transcript": transcript,
        "sentiment": sentiment_block,
        "post_conversation_summary": post_summary,
        "key_data_points": key_points,
    }


def advance_candidates_to_listwise_status(db: Session, candidate_ids: List[uuid.UUID]) -> None:
    for cid in candidate_ids:
        row = db.get(Candidate, cid)
        if row is None:
            continue
        if row.status == CandidateStatus.SENTIMENT_ANALYSIS:
            row.status = CandidateStatus.LISTWISE
