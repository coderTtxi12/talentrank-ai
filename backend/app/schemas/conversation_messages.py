"""Paginated screening chat messages for recruiter dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ConversationMessagePublic(BaseModel):
    id: str
    role: str = Field(description="user | assistant")
    content: str
    created_at: datetime


class ConversationMessagesPage(BaseModel):
    items: List[ConversationMessagePublic]
    next_cursor: Optional[str] = None
    limit: int
