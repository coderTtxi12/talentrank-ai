"""Read-only candidate listing with cursor pagination."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.database import Candidate, CandidateStatus, Language
from app.schemas.candidate_public import CandidatePublic, CandidatesCursorPage


def _language_to_country(lang: Language) -> str:
    if lang == Language.ES_ES:
        return "ES"
    return "MX"


def _currency_for_country(country: str) -> str:
    return "EUR" if country == "ES" else "MXN"


def candidate_to_public(row: Candidate) -> CandidatePublic:
    country = _language_to_country(row.language)
    status_val = row.status.value if isinstance(row.status, CandidateStatus) else str(row.status)
    full_name = row.full_name or ""
    doc_number = ""
    if row.phone:
        doc_number = row.phone[:32]
    elif row.email:
        doc_number = row.email[:32]

    return CandidatePublic(
        id=str(row.id),
        country_code=country,  # type: ignore[arg-type]
        document_type="CURP",
        document_number=doc_number,
        full_name=full_name,
        amount_requested=0.0,
        currency=_currency_for_country(country),
        monthly_income=0.0,
        status=status_val,
        risk_score=None,
        requires_review=bool(row.slot_uncertain),
        banking_info=None,
        extra_data=None,
        metadata=None,
        created_at=row.created_at,
        updated_at=row.updated_at,
        processed_at=None,
        created_by_id=None,
        reviewed_by_id=None,
    )


def _encode_cursor(created_at: datetime, cid: Any) -> str:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    payload = {
        "t": created_at.isoformat(),
        "id": str(cid),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, Any]:
    pad = "=" * (-len(cursor) % 4)
    raw = base64.urlsafe_b64decode(cursor + pad)
    payload = json.loads(raw.decode("utf-8"))
    t = datetime.fromisoformat(payload["t"])
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    import uuid

    cid = uuid.UUID(payload["id"])
    return t, cid


def list_candidates_cursor_page(
    db: Session,
    *,
    limit: int,
    cursor: Optional[str],
    status_filter: Optional[str],
    country_filter: Optional[str],
    include_total: bool,
) -> CandidatesCursorPage:
    stmt = select(Candidate)
    if status_filter:
        try:
            st = CandidateStatus(status_filter)
            stmt = stmt.where(Candidate.status == st)
        except ValueError:
            return CandidatesCursorPage(
                items=[],
                next_cursor=None,
                limit=limit,
                total=0 if include_total else None,
            )
    if country_filter == "ES":
        stmt = stmt.where(Candidate.language == Language.ES_ES)
    elif country_filter == "MX":
        stmt = stmt.where(Candidate.language == Language.ES_MX)

    stmt = stmt.order_by(Candidate.created_at.desc(), Candidate.id.desc())

    if cursor:
        t, cid = _decode_cursor(cursor)
        stmt = stmt.where(
            (Candidate.created_at < t)
            | ((Candidate.created_at == t) & (Candidate.id < cid))
        )

    rows = list(db.scalars(stmt.limit(limit + 1)).all())
    has_more = len(rows) > limit
    page_rows = rows[:limit]

    next_cursor: Optional[str] = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    total: Optional[int] = None
    if include_total:
        count_stmt = select(func.count()).select_from(Candidate)
        if status_filter:
            try:
                st = CandidateStatus(status_filter)
                count_stmt = count_stmt.where(Candidate.status == st)
            except ValueError:
                count_stmt = count_stmt.where(Candidate.status == status_filter)  # type: ignore[arg-type]
        if country_filter == "ES":
            count_stmt = count_stmt.where(Candidate.language == Language.ES_ES)
        elif country_filter == "MX":
            count_stmt = count_stmt.where(Candidate.language == Language.ES_MX)
        total = int(db.scalar(count_stmt) or 0)

    items = [candidate_to_public(r) for r in page_rows]
    return CandidatesCursorPage(
        items=items,
        next_cursor=next_cursor,
        limit=limit,
        total=total,
    )


def list_recent_candidates(db: Session, *, limit: int) -> list[CandidatePublic]:
    stmt = (
        select(Candidate)
        .order_by(Candidate.created_at.desc(), Candidate.id.desc())
        .limit(limit)
    )
    rows = list(db.scalars(stmt).all())
    return [candidate_to_public(r) for r in rows]


def get_candidate_by_id(db: Session, candidate_id: str) -> Optional[CandidatePublic]:
    import uuid

    try:
        uid = uuid.UUID(candidate_id)
    except ValueError:
        return None
    row = db.get(Candidate, uid)
    if row is None:
        return None
    return candidate_to_public(row)


def compute_statistics(db: Session) -> dict[str, Any]:
    """Derive dashboard statistics from candidates."""
    total = int(db.scalar(select(func.count()).select_from(Candidate)) or 0)

    by_status: dict[str, int] = {s.value: 0 for s in CandidateStatus}
    for st, cnt in db.execute(
        select(Candidate.status, func.count()).group_by(Candidate.status)
    ).all():
        key = st.value if hasattr(st, "value") else str(st)
        by_status[key] = int(cnt)

    es = int(
        db.scalar(
            select(func.count())
            .select_from(Candidate)
            .where(Candidate.language == Language.ES_ES)
        )
        or 0
    )
    mx = int(
        db.scalar(
            select(func.count())
            .select_from(Candidate)
            .where(Candidate.language == Language.ES_MX)
        )
        or 0
    )

    pending_review = int(
        db.scalar(
            select(func.count())
            .select_from(Candidate)
            .where(Candidate.slot_uncertain.is_(True))
        )
        or 0
    )

    return {
        "total_candidates": total,
        "total_loans": total,
        "total_count": total,
        "by_status": by_status,
        "by_country": {"ES": es, "MX": mx},
        "total_amount_requested": 0.0,
        "average_amount": None,
        "average_risk_score": None,
        "pending_review_count": pending_review,
    }
