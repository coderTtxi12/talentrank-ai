from fastapi import APIRouter, status

from app.core.logging import get_logger
from app.models.chat import ChatRequest, ChatResponse

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a candidate message to the screening agent",
    description=(
        "Receives a candidate message tied to a `session_id` and returns the "
        "agent reply. Placeholder: returns OK until the ReAct agent is wired in."
    ),
)
async def chat(payload: ChatRequest) -> ChatResponse:
    logger.info("chat turn received: session_id=%s len=%d", payload.session_id, len(payload.message))
    return ChatResponse(status="ok")
