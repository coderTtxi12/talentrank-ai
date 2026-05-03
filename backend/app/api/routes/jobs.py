"""Enqueue background jobs (listwise ranking)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database import Job, JobType
from app.schemas.listwise_job import CreateListwiseJobRequest, CreateListwiseJobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "/listwise",
    response_model=CreateListwiseJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue listwise ranking job",
    description=(
        "Inserts a `listwise` row into `jobs` and NOTIFYs `listwise_job_pending` "
        "so the listwise worker wakes without polling."
    ),
)
def create_listwise_job(
    body: CreateListwiseJobRequest,
    db: Session = Depends(get_db),
) -> CreateListwiseJobResponse:
    payload: dict = {}
    if body.vacancy_id is not None:
        payload["vacancy_id"] = str(body.vacancy_id)

    row = Job(
        job_type=JobType.LISTWISE,
        payload=payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CreateListwiseJobResponse(job_id=row.id)
