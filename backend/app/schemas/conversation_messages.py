"""Read models for screening **conversation messages** (dashboard transcript view).

Exposes durable ``messages`` rows in display order with cursor-based pagination.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ConversationMessagePublic(BaseModel):
    """One chat turn mirrored from PostgreSQL (role + content + timestamp)."""

    id: str
    role: str = Field(description="user | assistant")
    content: str
    created_at: datetime


class ConversationMessagesPage(BaseModel):
    """Page of transcript messages; ``next_cursor`` is None when no further pages."""

    items: List[ConversationMessagePublic]
    next_cursor: Optional[str] = None
    limit: int
