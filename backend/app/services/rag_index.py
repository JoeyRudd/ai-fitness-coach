"""Lightweight RAG index skeleton.

This is an intentionally *minimal* placeholder around a future embedding + FAISS
retrieval pipeline. It is kept pure (no FastAPI / framework deps) so it can be
unit‑tested easily. For now it only loads raw markdown/text documents and
`retrieve` returns an empty list until embedding + index construction is
implemented.

Planned architecture (future work):

    RAGIndex.load(path) -> scans directory for .md / .txt files, stores raw docs.
    RAGIndex.build() -> (TODO) create sentence embeddings with
        sentence-transformers 'all-MiniLM-L6-v2' (or configurable) and build a
        FAISS IndexFlatIP (cosine similarity via normalized vectors).
    RAGIndex.retrieve(query, k=4) -> (TODO) embed query, search FAISS, return top k snippets.

Design notes / TODOs:
- Add dependency: sentence-transformers (model: all-MiniLM-L6-v2) when implementing build().
- Add dependency: faiss-cpu (or faiss-gpu if appropriate) for vector index.
- Consider lightweight fallback (BM25 / simple keyword) if embeddings not available.
- Provide a small caching layer keyed by doc modification time to avoid rebuilding on every startup.
- Add truncation / chunking logic (e.g. 512-800 token chunks with overlap) before embedding; store mapping doc_chunk_id -> source metadata.

Current behavior:
- load() populates self._docs with (path, text) tuples.
- retrieve() returns [] unless (future) embedding index is built.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

@dataclass
class Document:
    path: str
    text: str

class RAGIndex:
    """In‑memory placeholder for a future vector index.

    Usage:
        idx = RAGIndex()
        idx.load('knowledge_base')
        results = idx.retrieve('what is training volume?')  # returns [] for now
    """

    def __init__(self) -> None:
        self._docs: List[Document] = []
        # Future fields (not yet used):
        self._embeddings = None  # type: ignore  # will hold ndarray or list[list[float]]
        self._index = None       # type: ignore  # will hold a FAISS index
        self._model = None       # type: ignore  # will hold a SentenceTransformer
        self._ready: bool = False

    # --------------------------- Loading ---------------------------
    def load(self, knowledge_path: str) -> None:
        """Load raw documents from a directory.

        Scans for .md and .txt files directly under the provided path (non‑recursive
        for now; adjust as needed). Stores full file contents.
        """
        p = Path(knowledge_path)
        if not p.exists() or not p.is_dir():
            logger.warning("Knowledge path does not exist or is not a directory: %s", knowledge_path)
            self._docs = []
            self._ready = False
            return
        docs: List[Document] = []
        for ext in ("*.md", "*.txt"):
            for file in p.glob(ext):
                try:
                    text = file.read_text(encoding="utf-8")
                    docs.append(Document(path=str(file), text=text))
                except Exception as e:  # noqa: BLE001
                    logger.error("Failed reading %s: %s", file, e)
        self._docs = docs
        # NOTE: We intentionally do *not* build embeddings here yet.
        self._ready = False
        logger.info("Loaded %d documents (embeddings not built).", len(self._docs))

    # --------------------------- Retrieval ------------------------
    def retrieve(self, query: str, k: int = 4) -> List[str]:
        """Retrieve top k document chunks relevant to the query.

        Placeholder: returns an empty list until embeddings + index are built.

        Future implementation outline (pseudo‑code):
            if not self._ready:
                self.build()  # lazily build
            q_vec = self._model.encode([query], normalize_embeddings=True)
            D, I = self._index.search(q_vec, k)
            return [self._chunks[i].text for i in I[0] if i >= 0]
        """
        if not self._ready or not self._docs or self._embeddings is None or self._index is None:
            return []
        # Unreachable until build() implemented.
        return []

__all__ = ["RAGIndex"]
