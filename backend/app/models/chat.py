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


class ChatResponse(BaseModel):
    """Reply produced by the agent (placeholder)."""

    status: str = Field(default="ok", description="Reply status flag.")
