"""candidate completed notify trigger

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-30

Adds a Postgres trigger that emits NOTIFY on the `candidate_completed` channel
whenever `candidates.is_completed` flips from false to true. The sentiment
analysis worker container subscribes to this channel via LISTEN, avoiding
constant polling against the database.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CHANNEL = "candidate_completed"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION notify_candidate_completed()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.is_completed = TRUE
               AND (OLD.is_completed IS DISTINCT FROM NEW.is_completed) THEN
                PERFORM pg_notify('{CHANNEL}', NEW.id::text);
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS candidate_completed_notify ON candidates;
        CREATE TRIGGER candidate_completed_notify
        AFTER UPDATE OF is_completed ON candidates
        FOR EACH ROW
        EXECUTE FUNCTION notify_candidate_completed();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS candidate_completed_notify ON candidates;")
    op.execute("DROP FUNCTION IF EXISTS notify_candidate_completed();")
