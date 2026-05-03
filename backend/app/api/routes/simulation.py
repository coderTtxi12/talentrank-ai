"""Dev / QA: load synthetic screening data (no OpenAI, no listwise)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.schemas.simulation import ScreeningSimulationSeedResponse
from app.services.simulation_screening_seed import seed_screening_simulation_batch

logger = get_logger(__name__)

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post(
    "/seed-screening-cohort",
    response_model=ScreeningSimulationSeedResponse,
    summary="Insert synthetic candidates + chats (+ optional sentiment rows)",
    description=(
        "Creates candidates with completed screening conversations and realistic fields. "
        "Some rows are HARD_DISQ (license or city coverage). "
        "All others are SENTIMENT_ANALYSIS with a persisted sentiment row, plausible reasoning, "
        "and start_date on the candidate and in transcript / key_data_points. "
        "Does not enqueue jobs or write ranking tables."
    ),
)
def post_seed_screening_cohort(
    count: int = Query(10, ge=1, le=100, description="Number of synthetic candidates."),
    db: Session = Depends(get_db),
) -> ScreeningSimulationSeedResponse:
    if not settings.ALLOW_SIMULATION_SEED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation seed is disabled (set ALLOW_SIMULATION_SEED=true).",
        )

    try:
        out = seed_screening_simulation_batch(db, count=count)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("simulation seed failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Simulation seed failed; database rolled back.",
        ) from exc

    logger.info(
        "simulation seed ok batch_id=%s count=%s breakdown=%s",
        out["batch_id"],
        out["inserted_candidates"],
        out.get("breakdown"),
    )
    return ScreeningSimulationSeedResponse(
        batch_id=out["batch_id"],
        inserted_candidates=out["inserted_candidates"],
        candidate_ids=out["candidate_ids"],
        breakdown=out.get("breakdown") or {},
    )
