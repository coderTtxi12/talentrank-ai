"""repair listwise job_type enum and notify trigger

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-03

Some databases were marked at revision 0004 without applying the enum/trigger
(e.g. `alembic stamp`). This revision re-applies those steps idempotently.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHANNEL = "listwise_job_pending"


def upgrade() -> None:
    # PG 15+ — no-op if label already exists (Idempotent for repaired DBs.)
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'listwise'")

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
