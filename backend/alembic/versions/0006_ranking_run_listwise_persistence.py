"""ranking persistence for listwise orchestrator

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-03

- ``ranking_runs.vacancy_id`` nullable (listwise job may omit vacancy).
- ``ranking_runs.orchestrator_output`` JSONB: orchestrator summary + coverage.
- ``ranking_tournaments.llm_trace`` JSONB: per-tournament instructions + rationale.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "ranking_runs",
        "vacancy_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "ranking_runs",
        sa.Column(
            "orchestrator_output",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "ranking_tournaments",
        sa.Column(
            "llm_trace",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("ranking_tournaments", "llm_trace")
    op.drop_column("ranking_runs", "orchestrator_output")
    op.execute("DELETE FROM ranking_runs WHERE vacancy_id IS NULL")
    op.alter_column(
        "ranking_runs",
        "vacancy_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
