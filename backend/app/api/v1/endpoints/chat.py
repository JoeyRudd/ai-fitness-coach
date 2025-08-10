from fastapi import APIRouter, HTTPException, Request
import logging
from app.models.chat import (
    HistoryChatRequest, HistoryChatResponse,
    ChatRequest, ChatResponse, ChatTurn, ChatMessage, Profile
)
from app.services.rag_service import rag_service

logger = logging.getLogger("fitness_coach")

router = APIRouter()

@router.get("/")
async def api_root() -> dict[str, str]:
    return {"status": "ok", "service": "chat"}

@router.post("/chat2", response_model=HistoryChatResponse)
async def chat2(req: HistoryChatRequest) -> HistoryChatResponse:  # legacy path
    return rag_service.get_ai_response(req.history)

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    # Log minimal request info for debugging
    try:
        logger.info("/chat request: prior_turns=%d new_msg_len=%d client=%s", len(req.history), len(req.message), request.client.host if request.client else 'unknown')
    except Exception:  # noqa: BLE001
        pass
    # Reconstruct full history including new user message
    history: list[ChatMessage] = []
    for t in req.history:
        history.append(ChatMessage(role=t.role, content=t.content))
    history.append(ChatMessage(role='user', content=req.message))

    # Use existing service logic
    result = rag_service.get_ai_response(history)

    # Map HistoryChatResponse to ChatResponse (same shape currently)
    return ChatResponse(
        response=result.response,
        profile=Profile(**result.profile.model_dump()),  # type: ignore
        tdee=result.tdee,
        missing=result.missing,
        asked_this_intent=result.asked_this_intent,
        intent=result.intent
    )
