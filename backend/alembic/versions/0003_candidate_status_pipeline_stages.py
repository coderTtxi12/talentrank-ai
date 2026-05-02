"""candidate status pipeline stages

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-01

Adds intermediate screening/ranking stages to `candidate_status_enum`:
hard_filter, sentiment_analysis, listwise, plackett_luce (after in_progress).

PostgreSQL cannot remove enum labels safely in downgrade; downgrade is a no-op.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_VALUES = (
    "hard_filter",
    "sentiment_analysis",
    "listwise",
    "plackett_luce",
)


def upgrade() -> None:
    for label in _NEW_VALUES:
        op.execute(
            f"ALTER TYPE candidate_status_enum ADD VALUE '{label}'"
        )


def downgrade() -> None:
    # ENUM labels cannot be dropped safely without table rewrite; leave type as-is.
    pass
