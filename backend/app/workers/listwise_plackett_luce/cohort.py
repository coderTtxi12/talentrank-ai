"""Load candidate cohorts and rich profiles for listwise ranking."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging import get_logger
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

logger = get_logger(__name__)

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
        "phone": cand.phone,
        "email": cand.email,
        "language": cand.language.value if hasattr(cand.language, "value") else str(cand.language),
        "drivers_license": cand.drivers_license,
        "city_zone": cand.city_zone,
        "availability": cand.availability.value if cand.availability else None,
        "preferred_schedule": cand.preferred_schedule.value if cand.preferred_schedule else None,
        "experience_years": cand.experience_years,
        "platforms": cand.platforms,
        "start_date": cand.start_date.isoformat() if cand.start_date is not None else None,
        "status": cand.status.value if hasattr(cand.status, "value") else str(cand.status),
        "is_completed": cand.is_completed,
        "slot_uncertain": cand.slot_uncertain,
        "created_at": cand.created_at.isoformat() if cand.created_at else None,
        "conversation_id": str(conv.id) if conv is not None else None,
        "session_id": conv.session_id if conv is not None else None,
        "conversation_language": (
            conv.language.value if conv is not None and hasattr(conv.language, "value") else None
        ),
        "conversation_channel": (
            conv.channel.value if conv is not None and hasattr(conv.channel, "value") else None
        ),
        "conversation_transcript": transcript,
        "sentiment": sentiment_block,
        "post_conversation_summary": post_summary,
        "key_data_points": key_points,
    }


def load_ranking_cards_for_ids(candidate_ids: List[uuid.UUID]) -> Dict[str, Dict[str, Any]]:
    """Carga fichas completas (ORM) solo para los UUID indicados — uso en subagentes."""

    with SessionLocal() as db:
        return {str(cid): build_candidate_ranking_card(db, cid) for cid in candidate_ids}


def advance_candidates_to_plackett_luce_status(
    db: Session, candidate_ids: List[uuid.UUID]
) -> None:
    """After listwise + Plackett–Luce aggregation, move pipeline stage forward."""

    advanced = 0
    missing = 0
    skipped_other_status = 0
    for cid in candidate_ids:
        row = db.get(Candidate, cid)
        if row is None:
            missing += 1
            continue
        if row.status == CandidateStatus.SENTIMENT_ANALYSIS:
            row.status = CandidateStatus.PLACKETT_LUCE
            advanced += 1
        else:
            skipped_other_status += 1
    logger.info(
        "PL cohort: advance status sentiment_analysis→plackett_luce "
        "advanced=%d missing_row=%d skipped_non_sentiment=%d (input_ids=%d)",
        advanced,
        missing,
        skipped_other_status,
        len(candidate_ids),
    )
