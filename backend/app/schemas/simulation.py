"""Response bodies for **development / QA** simulation routes.

Used when bulk-inserting synthetic screening data (candidates, chats, sentiment)
without calling external LLMs. Not intended for production exposure unless
``ALLOW_SIMULATION_SEED`` is enabled.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ScreeningSimulationSeedResponse(BaseModel):
    """Summary returned after a screening cohort seed run (ids + counts + breakdown)."""

    batch_id: str
    inserted_candidates: int
    candidate_ids: List[uuid.UUID]
    breakdown: Dict[str, Any] = Field(default_factory=dict)
