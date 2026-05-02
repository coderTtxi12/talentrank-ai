"""Recruiter-facing candidate list and detail (read-mostly, plus status patch)."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.database import Candidate, CandidateStatus, Language
from app.schemas.candidate_create import CandidateCreateRequest
from app.schemas.candidate_public import CandidatePublic, CandidatesCursorPage
from app.schemas.candidate_status import PatchCandidateStatusRequest
from app.realtime import broadcast
from app.services.candidate_list import (
    candidate_to_public,
    compute_statistics,
    get_candidate_by_id,
    list_candidates_cursor_page,
    list_recent_candidates,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get(
    "",
    response_model=CandidatesCursorPage,
    summary="List candidates (cursor pagination)",
    description="Returns a page of candidates ordered by newest first. Use `next_cursor` for the following page.",
)
def list_candidates(
    cursor: Optional[str] = Query(None, description="Opaque cursor from previous response."),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    country_code: Optional[str] = Query(None, pattern="^(ES|MX)$"),
    include_total: bool = Query(False),
    db: Session = Depends(get_db),
) -> CandidatesCursorPage:
    return list_candidates_cursor_page(
        db,
        limit=limit,
        cursor=cursor,
        status_filter=status_filter,
        country_filter=country_code,
        include_total=include_total,
    )


@router.get(
    "/recent",
    response_model=list[CandidatePublic],
    summary="Most recently created candidates",
)
def recent_candidates(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[CandidatePublic]:
    return list_recent_candidates(db, limit=limit)


@router.post(
    "",
    response_model=CandidatePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a candidate (dashboard)",
)
async def create_candidate(body: CandidateCreateRequest, db: Session = Depends(get_db)) -> CandidatePublic:
    lang = Language.ES_ES if body.country_code == "ES" else Language.ES_MX
    row = Candidate(
        full_name=body.full_name.strip(),
        language=lang,
        phone=body.document_number.strip()[:40] if body.document_number else None,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unique constraint failed (e.g. document/phone already registered).",
        ) from None
    db.refresh(row)
    logger.info("candidate_created id=%s", row.id)
    pub = candidate_to_public(row)
    await broadcast.emit_candidate_created(pub.model_dump(mode="json"))
    return pub


@router.get(
    "/statistics",
    summary="Dashboard aggregates",
)
def candidates_statistics(db: Session = Depends(get_db)) -> dict:
    return compute_statistics(db)


@router.get(
    "/{candidate_id}",
    response_model=CandidatePublic,
    summary="Get one candidate by id",
)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> CandidatePublic:
    row = get_candidate_by_id(db, candidate_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return row


@router.patch(
    "/{candidate_id}/status",
    response_model=CandidatePublic,
    summary="Update candidate funnel status",
)
async def patch_candidate_status(
    candidate_id: str,
    body: PatchCandidateStatusRequest,
    db: Session = Depends(get_db),
) -> CandidatePublic:
    try:
        uid = uuid.UUID(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id") from exc

    row = db.get(Candidate, uid)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    old_status = row.status.value if isinstance(row.status, CandidateStatus) else str(row.status)
    try:
        row.status = CandidateStatus(body.status)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status: {body.status}",
        ) from exc

    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(
        "candidate_status_updated id=%s new_status=%s",
        candidate_id,
        body.status,
    )
    pub = candidate_to_public(row)
    await broadcast.emit_candidate_status_changed(
        str(uid),
        old_status=old_status,
        new_status=body.status,
    )
    return pub


@router.get(
    "/{candidate_id}/history",
    response_model=list[dict],
    summary="Status history (stub)",
    description="Persistent history table may be added later; returns an empty list for now.",
)
def candidate_history(candidate_id: str) -> list[dict]:
    try:
        uuid.UUID(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id") from exc
    return []
