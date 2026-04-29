from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import handle_turn

logger = get_logger(__name__)


def _client_safe_detail(exc: Exception) -> str:
    """Surface root cause in development; hide in production."""

    if settings.DEBUG or settings.ENVIRONMENT.lower() == "development":
        return f"{type(exc).__name__}: {exc}"
    return "upstream LLM or storage failure"

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a candidate message and get the assistant reply",
    description=(
        "Loads conversation history (Redis with Postgres fallback), calls the "
        "configured LLM, persists the new user and assistant turns to Redis "
        "and Postgres in parallel, and returns the reply."
    ),
)
async def chat(payload: ChatRequest) -> ChatResponse:
    try:
        envelope = await handle_turn(payload.session_id, payload.message)
    except RuntimeError as exc:
        logger.error("chat misconfiguration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("chat failed: session_id=%s", payload.session_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_client_safe_detail(exc),
        ) from exc

    return ChatResponse.from_envelope(payload.session_id, envelope)
