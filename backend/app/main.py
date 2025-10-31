from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import chat
from app.core.config import settings
from app.services.rag_service import rag_service

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1")

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/")
async def root() -> dict[str, str]:
    rag_status = "not ready"
    rag_backend = "none"
    chunk_count = 0

    if rag_service and hasattr(rag_service, '_rag_index') and rag_service._rag_index and rag_service._rag_index._ready:
        rag_status = "ready"
        chunk_count = len(rag_service._rag_index._chunks)
        if hasattr(rag_service._rag_index._model, 'transform'):
            rag_backend = "tfidf"
        elif hasattr(rag_service._rag_index._model, 'encode'):
            rag_backend = "sentence-transformer"

    return {
        "message": "AI Fitness Coach running",
        "model": settings.openrouter_model,
        "rag_status": rag_status,
        "rag_backend": rag_backend,
        "rag_chunks": str(chunk_count),
    }
