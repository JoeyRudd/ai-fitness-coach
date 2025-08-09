from fastapi import APIRouter
from app.models.chat import HistoryChatRequest, HistoryChatResponse
from app.services.rag_service import tag_service

router = APIRouter()

@router.post("/chat2", response_model=HistoryChatResponse)
async def chat2(req: HistoryChatRequest) -> HistoryChatResponse:
    return tag_service.get_ai_response(req.history)
