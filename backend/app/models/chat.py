from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Inbound chat turn from the candidate."""

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Conversation session id (shared with Redis hot-path key).",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Raw user message.",
    )


LanguageLiteral = Literal["es-ES", "es-MX", "en"]
NextActionLiteral = Literal[
    "ask_field",
    "confirm",
    "answer_company_question",
    "recap",
    "close",
    "handoff",
]
CandidateStatusLiteral = Literal[
    "new",
    "in_progress",
    "qualified",
    "qualified_flagged",
    "soft_disq",
    "hard_disq",
    "waitlist",
    "abandoned",
]
SecurityFlagLiteral = Literal[
    "none",
    "prompt_injection",
    "system_prompt_leak",
    "role_hijack",
    "encoded_content",
    "off_topic_persistent",
]


class AgentEnvelope(BaseModel):
    """Structured JSON the screening agent produces on each turn."""

    reasoning: str = Field(default="", description="Brief internal rationale.")
    reply: str = Field(default="", description="User-facing message.")
    language: LanguageLiteral = Field(default="es-MX")
    state_updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Fields captured or corrected this turn (key -> value).",
    )
    next_action: NextActionLiteral = Field(default="ask_field")
    next_field_to_ask: Optional[str] = None
    candidate_status_hint: CandidateStatusLiteral = Field(default="in_progress")
    is_completed: bool = Field(
        default=False,
        description="True when screening is fully completed for this candidate.",
    )
    security_flag: SecurityFlagLiteral = Field(default="none")
    needs_human: bool = Field(default=False)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """Reply produced by the agent."""

    session_id: str = Field(..., description="Echo of the conversation session id.")
    reply: str = Field(..., description="Assistant reply text.")
    agent: AgentEnvelope = Field(
        ...,
        description="Structured agent output (reasoning, status hints, flags, ...).",
    )
    status: str = Field(default="ok", description="Reply status flag.")

    @classmethod
    def from_envelope(cls, session_id: str, envelope: Dict[str, Any]) -> "ChatResponse":
        agent = AgentEnvelope.model_validate(envelope)
        return cls(session_id=session_id, reply=agent.reply, agent=agent)
