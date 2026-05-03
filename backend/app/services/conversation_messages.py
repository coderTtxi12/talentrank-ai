"""Dashboard-facing transcript reader: all chat messages for one candidate.

Joins ``conversations`` ➜ ``messages`` for the given ``candidate_id``, filters
to user/assistant turns only, and returns rows in chronological order with
opaque **keyset** cursors (created_at + message id) for stable pagination.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import Conversation, Message, MessageRole
from app.schemas.conversation_messages import ConversationMessagePublic, ConversationMessagesPage


def _encode_cursor(created_at: datetime, message_id: uuid.UUID) -> str:
    """Build a URL-safe cursor token from sort position (timestamp + id)."""

    t = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    payload = {"t": t.isoformat(), "id": str(message_id)}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Inverse of :func:`_encode_cursor` (raises if malformed)."""

    pad = "=" * (-len(cursor) % 4)
    raw = base64.urlsafe_b64decode(cursor + pad)
    payload = json.loads(raw.decode("utf-8"))
    t = datetime.fromisoformat(payload["t"])
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    mid = uuid.UUID(payload["id"])
    return t, mid


def list_conversation_messages_for_candidate(
    db: Session,
    *,
    candidate_id: uuid.UUID,
    limit: int,
    cursor: Optional[str],
) -> ConversationMessagesPage:
    """Return the next page of transcript messages for ``candidate_id`` (ascending time)."""

    stmt = (
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.candidate_id == candidate_id,
            Message.role.in_([MessageRole.USER, MessageRole.ASSISTANT]),
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
    )

    if cursor:
        t, mid = _decode_cursor(cursor)
        stmt = stmt.where(
            (Message.created_at > t) | ((Message.created_at == t) & (Message.id > mid))
        )

    rows = list(db.scalars(stmt.limit(limit + 1)).all())
    has_more = len(rows) > limit
    page_rows = rows[:limit]

    next_cursor: Optional[str] = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    items = [
        ConversationMessagePublic(
            id=str(m.id),
            role=m.role.value,
            content=m.content,
            created_at=m.created_at,
        )
        for m in page_rows
    ]
    return ConversationMessagesPage(items=items, next_cursor=next_cursor, limit=limit)
