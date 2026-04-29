"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-28

Creates the full PostgreSQL schema described in docs/POSTGRESQL_DESIGN.md:
catalogs, vacancies, candidates, conversations & messages, jobs queue,
sentiment results, ranking pipeline (runs / tournaments / results),
security events, nudges and audit log.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Enum definitions (created once, referenced by columns)
# ---------------------------------------------------------------------------

# Column-associated ENUMs: create_type=False so op.create_table() does NOT emit
# CREATE TYPE again (we emit types once below via Enum.create(checkfirst=True)).
COUNTRY_ENUM = postgresql.ENUM("ES", "MX", name="country_enum", create_type=False)
LANGUAGE_ENUM = postgresql.ENUM(
    "es-ES", "es-MX", "en", name="language_enum", create_type=False
)
CHANNEL_ENUM = postgresql.ENUM(
    "web_chat", "voice", name="channel_enum", create_type=False
)
CANDIDATE_STATUS_ENUM = postgresql.ENUM(
    "new",
    "in_progress",
    "qualified",
    "qualified_flagged",
    "soft_disq",
    "hard_disq",
    "waitlist",
    "abandoned",
    name="candidate_status_enum",
    create_type=False,
)
AVAILABILITY_ENUM = postgresql.ENUM(
    "full_time", "part_time", "weekends", name="availability_enum", create_type=False
)
PREFERRED_SCHEDULE_ENUM = postgresql.ENUM(
    "morning",
    "afternoon",
    "evening",
    "flexible",
    name="preferred_schedule_enum",
    create_type=False,
)
CONVERSATION_STATUS_ENUM = postgresql.ENUM(
    "active",
    "completed",
    "abandoned",
    "closed_disq",
    name="conversation_status_enum",
    create_type=False,
)
MESSAGE_ROLE_ENUM = postgresql.ENUM(
    "user",
    "assistant",
    "system",
    "tool",
    name="message_role_enum",
    create_type=False,
)
JOB_TYPE_ENUM = postgresql.ENUM(
    "sentiment",
    "ranking",
    "nudge",
    name="job_type_enum",
    create_type=False,
)
JOB_STATUS_ENUM = postgresql.ENUM(
    "pending",
    "running",
    "done",
    "failed",
    "cancelled",
    name="job_status_enum",
    create_type=False,
)
SENTIMENT_ENUM = postgresql.ENUM(
    "positive",
    "neutral",
    "confused",
    "frustrated",
    name="sentiment_enum",
    create_type=False,
)
VACANCY_STATUS_ENUM = postgresql.ENUM(
    "open",
    "paused",
    "closed",
    name="vacancy_status_enum",
    create_type=False,
)
URGENCY_ENUM = postgresql.ENUM(
    "low", "medium", "high", name="urgency_enum", create_type=False
)
NUDGE_TYPE_ENUM = postgresql.ENUM(
    "light",
    "context",
    "value",
    "close",
    name="nudge_type_enum",
    create_type=False,
)
SECURITY_SEVERITY_ENUM = postgresql.ENUM(
    "low",
    "medium",
    "high",
    "critical",
    name="security_severity_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # Required for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Create ENUM types once (checkfirst=True). Column defs use create_type=False
    # so create_table does not try to CREATE TYPE again.
    for e in (
        postgresql.ENUM("ES", "MX", name="country_enum"),
        postgresql.ENUM("es-ES", "es-MX", "en", name="language_enum"),
        postgresql.ENUM("web_chat", "voice", name="channel_enum"),
        postgresql.ENUM(
            "new",
            "in_progress",
            "qualified",
            "qualified_flagged",
            "soft_disq",
            "hard_disq",
            "waitlist",
            "abandoned",
            name="candidate_status_enum",
        ),
        postgresql.ENUM(
            "full_time", "part_time", "weekends", name="availability_enum"
        ),
        postgresql.ENUM(
            "morning",
            "afternoon",
            "evening",
            "flexible",
            name="preferred_schedule_enum",
        ),
        postgresql.ENUM(
            "active",
            "completed",
            "abandoned",
            "closed_disq",
            name="conversation_status_enum",
        ),
        postgresql.ENUM(
            "user", "assistant", "system", "tool", name="message_role_enum"
        ),
        postgresql.ENUM(
            "sentiment", "ranking", "nudge", name="job_type_enum"
        ),
        postgresql.ENUM(
            "pending",
            "running",
            "done",
            "failed",
            "cancelled",
            name="job_status_enum",
        ),
        postgresql.ENUM(
            "positive",
            "neutral",
            "confused",
            "frustrated",
            name="sentiment_enum",
        ),
        postgresql.ENUM("open", "paused", "closed", name="vacancy_status_enum"),
        postgresql.ENUM("low", "medium", "high", name="urgency_enum"),
        postgresql.ENUM(
            "light",
            "context",
            "value",
            "close",
            name="nudge_type_enum",
        ),
        postgresql.ENUM(
            "low",
            "medium",
            "high",
            "critical",
            name="security_severity_enum",
        ),
    ):
        e.create(bind, checkfirst=True)

    # ---------------------------------------------------------------- catalogs
    op.create_table(
        "service_areas",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("country", COUNTRY_ENUM, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_service_areas_country", "service_areas", ["country"])

    op.create_table(
        "service_zones",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "area_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_areas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.UniqueConstraint("area_id", "name", name="uq_zone_per_area"),
    )

    op.create_table(
        "platforms",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )

    # --------------------------------------------------------------- vacancies
    op.create_table(
        "vacancies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "area_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_areas.id"),
            nullable=False,
        ),
        sa.Column(
            "urgency",
            URGENCY_ENUM,
            nullable=False,
            server_default=sa.text("'medium'"),
        ),
        sa.Column(
            "critical_shifts",
            postgresql.ARRAY(sa.String(32)),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        sa.Column("ideal_start_days", sa.Integer, nullable=False, server_default=sa.text("3")),
        sa.Column("headcount", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column(
            "status",
            VACANCY_STATUS_ENUM,
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_vacancies_status_area", "vacancies", ["status", "area_id"])

    # -------------------------------------------------------------- candidates
    op.create_table(
        "candidates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("full_name", sa.String(160)),
        sa.Column("phone", sa.String(40), unique=True),
        sa.Column("email", sa.String(160), unique=True),
        sa.Column(
            "language",
            LANGUAGE_ENUM,
            nullable=False,
            server_default=sa.text("'es-MX'"),
        ),
        sa.Column("consent", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("consent_at", sa.DateTime(timezone=True)),
        sa.Column("drivers_license", sa.Boolean),
        sa.Column(
            "area_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_areas.id"),
        ),
        sa.Column(
            "zone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_zones.id"),
        ),
        sa.Column("availability", AVAILABILITY_ENUM),
        sa.Column("preferred_schedule", PREFERRED_SCHEDULE_ENUM),
        sa.Column("experience_years", sa.Integer),
        sa.Column("platforms", postgresql.ARRAY(sa.String(64))),
        sa.Column("start_date", sa.Date),
        sa.Column(
            "status",
            CANDIDATE_STATUS_ENUM,
            nullable=False,
            server_default=sa.text("'new'"),
        ),
        sa.Column(
            "slot_uncertain", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("experience_years IS NULL OR experience_years BETWEEN 0 AND 50"),
    )
    op.create_index("ix_candidates_status", "candidates", ["status"])
    op.create_index("ix_candidates_area_status", "candidates", ["area_id", "status"])

    # ----------------------------------------------------------- conversations
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", sa.String(80), nullable=False, unique=True),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "vacancy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vacancies.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "channel",
            CHANNEL_ENUM,
            nullable=False,
            server_default=sa.text("'web_chat'"),
        ),
        sa.Column(
            "language",
            LANGUAGE_ENUM,
            nullable=False,
            server_default=sa.text("'es-MX'"),
        ),
        sa.Column(
            "status",
            CONVERSATION_STATUS_ENUM,
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "captured_data",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("summary", sa.Text),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_conv_status", "conversations", ["status"])
    op.create_index("ix_conv_candidate", "conversations", ["candidate_id"])
    op.create_index("ix_conv_vacancy", "conversations", ["vacancy_id"])

    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", MESSAGE_ROLE_ENUM, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("language", LANGUAGE_ENUM),
        sa.Column(
            "security_flagged",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("tool_calls", postgresql.JSONB),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_messages_conv_created", "messages", ["conversation_id", "created_at"]
    )

    # ---------------------------------------------------------------- jobs
    op.create_table(
        "jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("job_type", JOB_TYPE_ENUM, nullable=False),
        sa.Column(
            "status",
            JOB_STATUS_ENUM,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "payload",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "max_attempts", sa.Integer, nullable=False, server_default=sa.text("5")
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("locked_by", sa.String(120)),
        sa.Column(
            "run_after",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_error", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    # Partial index for the worker hot path: only pending rows.
    op.execute(
        "CREATE INDEX ix_jobs_pending_runafter ON jobs (job_type, run_after) "
        "WHERE status = 'pending'"
    )

    # ---------------------------------------------------------- sentiment
    op.create_table(
        "sentiment_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("sentiment", SENTIMENT_ENUM, nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column(
            "signals",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --------------------------------------------------------------- ranking
    op.create_table(
        "ranking_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "vacancy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vacancies.id"),
            nullable=False,
        ),
        sa.Column("rubric_version", sa.String(40), nullable=False),
        sa.Column("pool_size", sa.Integer, nullable=False),
        sa.Column("top_n", sa.Integer, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column(
            "status",
            JOB_STATUS_ENUM,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    op.create_index("ix_rrun_vacancy_started", "ranking_runs", ["vacancy_id", "started_at"])

    op.create_table(
        "ranking_tournaments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ranking_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column(
            "llm_ranking",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column(
            "is_active_learning",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_rtour_run", "ranking_tournaments", ["run_id"])

    op.create_table(
        "ranking_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ranking_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.id"),
            nullable=False,
        ),
        sa.Column("utility", sa.Numeric(8, 4), nullable=False),
        sa.Column("posterior_variance", sa.Numeric(8, 4), nullable=False),
        sa.Column("rank_position", sa.Integer, nullable=False),
        sa.Column("tournaments_seen", sa.Integer, nullable=False),
        sa.Column(
            "decision_trace",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.UniqueConstraint("run_id", "candidate_id", name="uq_rresult_run_candidate"),
    )
    op.create_index(
        "ix_rresult_run_position", "ranking_results", ["run_id", "rank_position"]
    )

    # -------------------------------------------------- security & nudges & audit
    op.create_table(
        "security_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
        ),
        sa.Column("attack_type", sa.String(80), nullable=False),
        sa.Column("severity", SECURITY_SEVERITY_ENUM, nullable=False),
        sa.Column("pattern", sa.Text),
        sa.Column("raw_input", sa.Text),
        sa.Column("blocked", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "extra",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_secev_conv_created", "security_events", ["conversation_id", "created_at"])
    op.create_index("ix_secev_attack", "security_events", ["attack_type"])

    op.create_table(
        "nudges",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nudge_type", NUDGE_TYPE_ENUM, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("delivered", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_nudges_due", "nudges", ["scheduled_at", "delivered"])

    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_entity", "audit_log", ["entity_type", "entity_id"])


def downgrade() -> None:
    bind = op.get_bind()

    for tbl in (
        "audit_log",
        "nudges",
        "security_events",
        "ranking_results",
        "ranking_tournaments",
        "ranking_runs",
        "sentiment_results",
        "jobs",
        "messages",
        "conversations",
        "candidates",
        "vacancies",
        "platforms",
        "service_zones",
        "service_areas",
    ):
        op.drop_table(tbl)

    for e in (
        SECURITY_SEVERITY_ENUM,
        NUDGE_TYPE_ENUM,
        URGENCY_ENUM,
        VACANCY_STATUS_ENUM,
        SENTIMENT_ENUM,
        JOB_STATUS_ENUM,
        JOB_TYPE_ENUM,
        MESSAGE_ROLE_ENUM,
        CONVERSATION_STATUS_ENUM,
        PREFERRED_SCHEDULE_ENUM,
        AVAILABILITY_ENUM,
        CANDIDATE_STATUS_ENUM,
        CHANNEL_ENUM,
        LANGUAGE_ENUM,
        COUNTRY_ENUM,
    ):
        e.drop(bind, checkfirst=True)
