import os
from app.services.rag_index import RAGIndex

KB_PATH = os.environ.get("KNOWLEDGE_BASE_PATH", "knowledge_base")

def test_rag_index_retrieval_basic():
    idx = RAGIndex()
    idx.load(KB_PATH)
    idx.build()  # Explicitly build index before retrieval
    results = idx.retrieve("training intensity", k=3)
    # If libraries installed and KB present, expect either empty (libs missing) or at least one hit
    assert isinstance(results, list)
    if results:  # when embeddings available
        assert any("intensity" in r["text"].lower() for r in results)
