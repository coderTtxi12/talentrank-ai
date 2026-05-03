"""listwise job type and notify trigger

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-02

Adds `listwise` to `job_type_enum` and a trigger that NOTIFYs the
`listwise_job_pending` channel on INSERT of listwise jobs so workers can wake
from sleep without polling.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHANNEL = "listwise_job_pending"


def upgrade() -> None:
    op.execute("ALTER TYPE job_type_enum ADD VALUE 'listwise'")

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION notify_listwise_job_pending()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.job_type::text = 'listwise' THEN
                PERFORM pg_notify('{CHANNEL}', NEW.id::text);
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS listwise_job_pending_notify ON jobs;
        CREATE TRIGGER listwise_job_pending_notify
        AFTER INSERT ON jobs
        FOR EACH ROW
        EXECUTE FUNCTION notify_listwise_job_pending();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS listwise_job_pending_notify ON jobs;")
    op.execute("DROP FUNCTION IF EXISTS notify_listwise_job_pending();")
    # ENUM label 'listwise' is left in place (PostgreSQL cannot drop safely).
