"""SQLAlchemy ORM models — persistent state.

Design principles:
- PostgreSQL only (we rely on JSONB, ARRAY and ENUM types).
- Lookup catalogs (`service_areas`) are tables, not enums in code.
- Free-form, evolving payloads (LLM traces, sentiment signals, rubric, etc.)
  live in JSONB columns.
- Surrogate UUID PKs everywhere; natural keys (e.g. `code`) are unique.
- All timestamps are `TIMESTAMPTZ` and default to `now()` server-side.
- License is captured ONLY as a boolean from chat — no image storage.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

# NOTE: Python 3.9 — use Optional/List/Dict instead of PEP604 (|) in Mapped[]
# so SQLAlchemy can resolve annotations when importing models (Alembic).

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Declarative base. Importing this module registers every model on it."""


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """PostgreSQL ENUM labels ↔ Python Enum `.value` (not member names).

    Without this, loading rows can raise ``LookupError: 'web_chat' is not among
    the defined enum values … Possible values: WEB_CHAT, VOICE``.
    """

    return [member.value for member in enum_cls]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Country(str, enum.Enum):
    ES = "ES"
    MX = "MX"


class Language(str, enum.Enum):
    ES_ES = "es-ES"
    ES_MX = "es-MX"
    EN = "en"


class Channel(str, enum.Enum):
    WEB_CHAT = "web_chat"
    VOICE = "voice"


class CandidateStatus(str, enum.Enum):
    NEW = "new"
    # Conversational screening with the IA agent (requirements capture).
    IN_PROGRESS = "in_progress"
    # Mandatory-requirements gate (hard filter / CP-1 style evaluation).
    HARD_FILTER = "hard_filter"
    # Sentiment analysis over the conversation transcript.
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    # Listwise ranking stage (ordering candidates as a list).
    LISTWISE = "listwise"
    # Plackett–Luce pairwise / choice ranking stage.
    PLACKETT_LUCE = "plackett_luce"
    QUALIFIED = "qualified"
    QUALIFIED_FLAGGED = "qualified_flagged"
    SOFT_DISQ = "soft_disq"
    HARD_DISQ = "hard_disq"
    WAITLIST = "waitlist"
    ABANDONED = "abandoned"


class Availability(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    WEEKENDS = "weekends"


class PreferredSchedule(str, enum.Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    FLEXIBLE = "flexible"


class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    CLOSED_DISQ = "closed_disq"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class JobType(str, enum.Enum):
    SENTIMENT = "sentiment"
    RANKING = "ranking"
    LISTWISE = "listwise"
    NUDGE = "nudge"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Sentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"


class VacancyStatus(str, enum.Enum):
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"


class Urgency(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NudgeType(str, enum.Enum):
    LIGHT = "light"
    CONTEXT = "context"
    VALUE = "value"
    CLOSE = "close"


class SecuritySeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Catalogs
# ---------------------------------------------------------------------------


class ServiceArea(Base):
    """City inside the 45 service areas (ES + MX)."""

    __tablename__ = "service_areas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[Country] = mapped_column(
        SAEnum(Country, name="country_enum", values_callable=_enum_values), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    zones: Mapped[List["ServiceZone"]] = relationship(
        back_populates="area", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_service_areas_country", "country"),)


class ServiceZone(Base):
    """Sub-zone inside a service area (optional refinement)."""

    __tablename__ = "service_zones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_areas.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    area: Mapped[ServiceArea] = relationship(back_populates="zones")

    __table_args__ = (UniqueConstraint("area_id", "name", name="uq_zone_per_area"),)


# ---------------------------------------------------------------------------
# Vacancies
# ---------------------------------------------------------------------------


class Vacancy(Base):
    """Open hiring need at a service area."""

    __tablename__ = "vacancies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_areas.id"), nullable=False
    )
    urgency: Mapped[Urgency] = mapped_column(
        SAEnum(Urgency, name="urgency_enum", values_callable=_enum_values), nullable=False, server_default=text("'medium'")
    )
    critical_shifts: Mapped[List[str]] = mapped_column(
        ARRAY(String(32)), nullable=False, server_default=text("'{}'::varchar[]")
    )
    ideal_start_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    headcount: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    status: Mapped[VacancyStatus] = mapped_column(
        SAEnum(VacancyStatus, name="vacancy_status_enum", values_callable=_enum_values),
        nullable=False,
        server_default=text("'open'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_vacancies_status_area", "status", "area_id"),)


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


class Candidate(Base):
    """A person screened by the agent.

    License is a boolean asked via chat — no image, no document attachment.
    `phone` and `email` are optional and only populated if/when the candidate
    provides them.
    """

    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(160))
    phone: Mapped[Optional[str]] = mapped_column(String(40), unique=True)
    email: Mapped[Optional[str]] = mapped_column(String(160), unique=True)
    language: Mapped[Language] = mapped_column(
        SAEnum(Language, name="language_enum", values_callable=_enum_values), nullable=False, server_default=text("'es-MX'")
    )

    # Screening data (asked through chat — license is a boolean only)
    drivers_license: Mapped[Optional[bool]] = mapped_column(Boolean)
    city_zone: Mapped[Optional[str]] = mapped_column(String(200))
    availability: Mapped[Optional[Availability]] = mapped_column(
        SAEnum(Availability, name="availability_enum", values_callable=_enum_values)
    )
    preferred_schedule: Mapped[Optional[PreferredSchedule]] = mapped_column(
        SAEnum(PreferredSchedule, name="preferred_schedule_enum", values_callable=_enum_values)
    )
    experience_years: Mapped[Optional[int]] = mapped_column(Integer)
    platforms: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(64)))
    start_date: Mapped[Optional[date]] = mapped_column(Date)

    status: Mapped[CandidateStatus] = mapped_column(
        SAEnum(CandidateStatus, name="candidate_status_enum", values_callable=_enum_values),
        nullable=False,
        server_default=text("'new'"),
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    slot_uncertain: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    conversations: Mapped[List["Conversation"]] = relationship(back_populates="candidate")

    __table_args__ = (
        CheckConstraint("experience_years IS NULL OR experience_years BETWEEN 0 AND 50"),
        Index("ix_candidates_status", "status"),
    )


# ---------------------------------------------------------------------------
# Conversations & messages
# ---------------------------------------------------------------------------


class Conversation(Base):
    """One screening session.

    `session_id` is the same key used by Redis (hot-path conversation state and
    rolling history live there with TTL — see REDIS_DESIGN.md). Postgres keeps
    the durable, queryable copy.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="SET NULL")
    )
    vacancy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vacancies.id", ondelete="SET NULL")
    )
    channel: Mapped[Channel] = mapped_column(
        SAEnum(Channel, name="channel_enum", values_callable=_enum_values), nullable=False, server_default=text("'web_chat'")
    )
    language: Mapped[Language] = mapped_column(
        SAEnum(Language, name="language_enum", values_callable=_enum_values), nullable=False, server_default=text("'es-MX'")
    )
    status: Mapped[ConversationStatus] = mapped_column(
        SAEnum(ConversationStatus, name="conversation_status_enum", values_callable=_enum_values),
        nullable=False,
        server_default=text("'active'"),
    )
    captured_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    summary: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    candidate: Mapped[Optional["Candidate"]] = relationship(back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_conv_status", "status"),
        Index("ix_conv_candidate", "candidate_id"),
        Index("ix_conv_vacancy", "vacancy_id"),
    )


class Message(Base):
    """One turn in a conversation. Mirrors what's in Redis history."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(MessageRole, name="message_role_enum", values_callable=_enum_values), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Optional[Language]] = mapped_column(
        SAEnum(Language, name="language_enum", values_callable=_enum_values)
    )
    security_flagged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    tool_calls: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_messages_conv_created", "conversation_id", "created_at"),)


# ---------------------------------------------------------------------------
# Worker queue (consumed by sentiment + ranking workers)
# ---------------------------------------------------------------------------


class Job(Base):
    """Generic job queue table.

    Workers SELECT ... FOR UPDATE SKIP LOCKED to claim work. `payload` carries
    the per-job parameters (e.g. `{"conversation_id": "..."}` or
    `{"vacancy_id": "..."}`).
    """

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    job_type: Mapped[JobType] = mapped_column(
        SAEnum(JobType, name="job_type_enum", values_callable=_enum_values), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status_enum", values_callable=_enum_values),
        nullable=False,
        server_default=text("'pending'"),
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("5"))
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[Optional[str]] = mapped_column(String(120))
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_jobs_pending_runafter",
            "job_type",
            "run_after",
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_jobs_status", "status"),
    )


# ---------------------------------------------------------------------------
# Sentiment results
# ---------------------------------------------------------------------------


class SentimentResult(Base):
    __tablename__ = "sentiment_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    sentiment: Mapped[Sentiment] = mapped_column(
        SAEnum(Sentiment, name="sentiment_enum", values_callable=_enum_values), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    signals: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Ranking (Listwise + Plackett–Luce)
# ---------------------------------------------------------------------------


class RankingRun(Base):
    """One full execution of the ranking pipeline for a vacancy."""

    __tablename__ = "ranking_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vacancies.id"), nullable=False
    )
    rubric_version: Mapped[str] = mapped_column(String(40), nullable=False)
    pool_size: Mapped[int] = mapped_column(Integer, nullable=False)
    top_n: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status_enum", values_callable=_enum_values),
        nullable=False,
        server_default=text("'pending'"),
    )

    tournaments: Mapped[List["RankingTournament"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    results: Mapped[List["RankingResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_rrun_vacancy_started", "vacancy_id", "started_at"),)


class RankingTournament(Base):
    """One listwise LLM call over a subset of K candidates."""

    __tablename__ = "ranking_tournaments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ranking_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_ids: Mapped[List[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False
    )
    llm_ranking: Mapped[List[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active_learning: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run: Mapped[RankingRun] = relationship(back_populates="tournaments")

    __table_args__ = (Index("ix_rtour_run", "run_id"),)


class RankingResult(Base):
    """Per-candidate Plackett–Luce result inside a run."""

    __tablename__ = "ranking_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ranking_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False
    )
    utility: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    posterior_variance: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    tournaments_seen: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_trace: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    run: Mapped[RankingRun] = relationship(back_populates="results")

    __table_args__ = (
        UniqueConstraint("run_id", "candidate_id", name="uq_rresult_run_candidate"),
        Index("ix_rresult_run_position", "run_id", "rank_position"),
    )


# ---------------------------------------------------------------------------
# Reflection / security events
# ---------------------------------------------------------------------------


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL")
    )
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL")
    )
    attack_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[SecuritySeverity] = mapped_column(
        SAEnum(SecuritySeverity, name="security_severity_enum", values_callable=_enum_values), nullable=False
    )
    pattern: Mapped[Optional[str]] = mapped_column(Text)
    raw_input: Mapped[Optional[str]] = mapped_column(Text)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    extra: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_secev_conv_created", "conversation_id", "created_at"),
        Index("ix_secev_attack", "attack_type"),
    )


# ---------------------------------------------------------------------------
# Re-engagement nudges
# ---------------------------------------------------------------------------


class Nudge(Base):
    __tablename__ = "nudges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    nudge_type: Mapped[NudgeType] = mapped_column(
        SAEnum(NudgeType, name="nudge_type_enum", values_callable=_enum_values), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    __table_args__ = (Index("ix_nudges_due", "scheduled_at", "delivered"),)


# ---------------------------------------------------------------------------
# Audit log (GDPR / EU AI Act traceability)
# ---------------------------------------------------------------------------


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)
