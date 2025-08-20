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

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import List, Optional, Dict, Any

# Make model_config import optional since we removed ML dependencies
try:
    from app.core.model_config import MODEL_CONFIG
except ImportError:
    MODEL_CONFIG = {"sentence_transformer_model": "all-MiniLM-L6-v2"}

logger = logging.getLogger(__name__)

try:  # TF-IDF vectorizer (much faster and smaller than sentence transformers)
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # noqa: BLE001
    TfidfVectorizer = None  # type: ignore
    cosine_similarity = None  # type: ignore

try:  # sentence transformers (fallback if available)
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # noqa: BLE001
    SentenceTransformer = None  # type: ignore

# faiss now optional; if missing we use pure numpy cosine similarity
try:  # pragma: no cover
    import faiss  # type: ignore
except Exception:  # noqa: BLE001
    faiss = None  # type: ignore

try:
    import numpy as np  # lightweight dependency already present (torch pulls it in)
except ImportError:
    np = None  # type: ignore

try:  # BM25 for better short query handling
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except Exception:  # noqa: BLE001
    BM25_AVAILABLE = False  # type: ignore

# --------------------------- Data Classes ---------------------------
@dataclass
class Document:
    path: str
    text: str

@dataclass
class Chunk:
    doc_path: str
    text: str
    idx: int

# --------------------------- Constants ---------------------------
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
MAX_CHUNK_HARD = 1200
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

SYNONYMS = {
    "tdee": ["maintenance calories", "daily burn"],
    "cut": ["deficit", "weight loss"],
    "bulk": ["surplus", "gain muscle", "hypertrophy"],
    "protein": ["protein intake", "macros"],
    "workout": ["routine", "program", "plan"],
    "cardio": ["aerobic", "conditioning"],
}

def _expand_query(q: str) -> str:
    ql = q.lower()
    extra = []
    for k, vs in SYNONYMS.items():
        if k in ql:
            extra.extend(vs)
    return q if not extra else f"{q} " + " ".join(extra)

logger = logging.getLogger(__name__)

class RAGIndex:
    """Lightweight embedding + FAISS index for local markdown knowledge base.

    Public methods:
        load(path): read .md/.txt recursively
        build(model_name): chunk + embed + build FAISS (lazy)
        retrieve(query, k): semantic search returning list[dict]
    """

    def __init__(self) -> None:
        self._docs: List[Document] = []
        self._chunks: List[Chunk] = []
        self._embeddings: Optional[Any] = None  # shape (N, D) - numpy array when available
        self._index = None  # faiss index if available
        self._model: Optional[Any] = None
        self._ready = False
        self._built = False
        self._building = False
        self._model_name: Optional[str] = None
        self._last_build: float = 0.0

    # --------------------------- Loading ---------------------------
    def load(self, knowledge_path: str) -> None:
        p = Path(knowledge_path)
        if not p.exists() or not p.is_dir():
            logger.warning("Knowledge path does not exist or is not a directory: %s", knowledge_path)
            self._docs = []
            self._invalidate()
            return
        docs: List[Document] = []
        for file in p.rglob('*'):
            if not file.is_file():
                continue
            if file.suffix.lower() not in ('.md', '.txt'):
                continue
            try:
                text = file.read_text(encoding='utf-8').strip()
                if not text:
                    continue
                docs.append(Document(path=str(file), text=text))
            except Exception as e:  # noqa: BLE001
                logger.error("Failed reading %s: %s", file, e)
        self._docs = docs
        self._invalidate()
        logger.info("Loaded %d documents (index not built yet).", len(self._docs))

    def _invalidate(self) -> None:
        self._chunks = []
        self._embeddings = None
        self._index = None
        self._ready = False
        self._built = False
        self._model = None
        self._model_name = None

    # --------------------------- Chunking ---------------------------
    def _chunk_docs(self) -> None:
        if not self._docs:
            self._chunks = []
            return
        chunks: List[Chunk] = []
        for doc in self._docs:
            raw = doc.text
            if not raw:
                continue
            # Split into paragraphs first
            paragraphs = [b.strip() for b in raw.split('\n\n') if b.strip()]
            parts: List[str] = []
            for block in paragraphs:
                if len(block) <= CHUNK_SIZE:
                    parts.append(block)
                else:
                    # Further split sentences
                    sentences = _SENT_SPLIT.split(block)
                    buf = ''
                    for s in sentences:
                        s = s.strip()
                        if not s:
                            continue
                        if buf and len(buf) + 1 + len(s) > CHUNK_SIZE:
                            parts.append(buf)
                            buf = s
                        else:
                            buf = (buf + ' ' + s).strip()
                    if buf:
                        parts.append(buf)
            # Re-pack with overlap
            assembled: List[str] = []
            current = ''
            for ptxt in parts:
                if not current:
                    current = ptxt
                    continue
                if len(current) + 2 + len(ptxt) <= CHUNK_SIZE:
                    current += '\n' + ptxt
                else:
                    assembled.append(current)
                    tail = current[-CHUNK_OVERLAP:]
                    current = tail + '\n' + ptxt
            if current:
                assembled.append(current)
            for i, txt in enumerate(assembled):
                if len(txt) > MAX_CHUNK_HARD:
                    txt = txt[:MAX_CHUNK_HARD]
                h1 = re.search(r"^#\s+(.+)", raw, re.M)
                h2 = re.search(r"^##\s+(.+)", raw, re.M)
                title = h1.group(1).strip() if h1 else Path(doc.path).stem
                subtitle = h2.group(1).strip() if h2 else ""
                header = f"{title} — {subtitle}" if subtitle else title
                txt = f"{header}\n{txt}".strip()
                chunks.append(Chunk(doc_path=doc.path, text=txt.strip(), idx=i))
        # Optional de-duplication
        seen: Dict[str, int] = {}
        unique: List[Chunk] = []
        for c in chunks:
            key = c.text[:400]
            if key in seen:
                continue
            seen[key] = 1
            unique.append(c)
        self._chunks = unique

    # --------------------------- Build ---------------------------
    def build(self, model_name: str = None) -> None:
        if self._built or self._building:
            return
        if not self._docs:
            logger.warning("No documents to build RAG index.")
            return
        
        try:
            self._building = True
            self._chunk_docs()
            if not self._chunks:
                logger.warning("No chunks produced; build aborted.")
                return
            
            texts = [c.text for c in self._chunks]
            
            # Try TF-IDF first (fast and lightweight)
            if TfidfVectorizer is not None and cosine_similarity is not None:
                self._model = TfidfVectorizer(
                    max_features=5000,
                    stop_words='english',
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_df=0.9
                )
                self._embeddings = self._model.fit_transform(texts)
                self._ready = True
                self._built = True
                self._last_build = time()
                logger.info("RAG index built with TF-IDF: %d chunks", len(self._chunks))
                return
            
            # Try BM25 if available (excellent for short queries)
            if BM25_AVAILABLE:
                try:
                    # Tokenize texts for BM25
                    tokenized_texts = [text.lower().split() for text in texts]
                    self._bm25_index = BM25Okapi(tokenized_texts)
                    self._model = "bm25"  # Mark as BM25 model
                    self._ready = True
                    self._built = True
                    self._last_build = time()
                    logger.info("RAG index built with BM25: %d chunks", len(self._chunks))
                    return
                except Exception as e:  # noqa: BLE001
                    logger.warning("BM25 index creation failed: %s", e)
                    # Continue to sentence transformers fallback
            
            # Fallback to sentence transformers if available
            if SentenceTransformer is not None and np is not None:
                model_name = model_name or MODEL_CONFIG.get("sentence_transformer_model", "all-MiniLM-L6-v2") if MODEL_CONFIG else "all-MiniLM-L6-v2"
                self._model_name = model_name
                self._model = SentenceTransformer(model_name)
                emb = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False).astype("float32")
                self._embeddings = emb
                
                if faiss is not None:
                    try:
                        dim = emb.shape[1]
                        index = faiss.IndexFlatIP(dim)
                        index.add(emb)
                        self._index = index
                    except Exception as e:  # noqa: BLE001
                        logger.warning("FAISS index creation failed; falling back to pure NumPy: %s", e)
                        self._index = None
                
                self._ready = True
                self._built = True
                self._last_build = time()
                logger.info("RAG index built with sentence transformers: %d chunks", len(self._chunks))
                return
            
            logger.warning("No suitable RAG backend available (missing sklearn or sentence-transformers)")
            
        except Exception as e:  # noqa: BLE001
            logger.warning("RAGIndex build failed: %s", e)
            self._invalidate()
        finally:
            self._building = False

    # --------------------------- Retrieval ---------------------------
    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, str]]:
        if not query or not query.strip():
            return []
        if not self._ready:
            self.build()
            if not self._ready:
                return []
        if not self._model or self._embeddings is None:
            return self._keyword_fallback(query, k)
        
        try:
            query = _expand_query(query)
            # TF-IDF approach
            if hasattr(self._model, 'transform'):  # TfidfVectorizer
                q_vec = self._model.transform([query])
                scores = cosine_similarity(q_vec, self._embeddings).flatten()
                # Small boost when query terms appear in the chunk header line
                try:
                    header_terms = set(re.findall(r"\w+", (query or "").lower()))
                    if header_terms is not None and len(header_terms) > 0:
                        for i in range(len(self._chunks)):
                            first_line = self._chunks[i].text.split("\n", 1)[0].lower()
                            if any(t in first_line for t in header_terms):
                                scores[i] *= 1.12
                except Exception:  # noqa: BLE001
                    pass
                if len(scores) == 0:
                    return []
                topk = min(k, len(scores))
                indices = np.argsort(scores)[-topk:][::-1]  # descending order
                
            # BM25 approach
            elif self._model == "bm25" and hasattr(self, '_bm25_index'):
                try:
                    scores = self._bm25_index.get_scores(query.lower().split())
                    if len(scores) == 0:
                        return []
                    topk = min(k, len(scores))
                    indices = np.argsort(-scores)[:topk]  # descending order
                except Exception as e:  # noqa: BLE001
                    logger.warning("BM25 retrieval failed: %s", e)
                    return []
                
            # Sentence transformer approach
            elif hasattr(self._model, 'encode'):  # SentenceTransformer
                if np is None:
                    return []
                q_emb = self._model.encode([query], normalize_embeddings=True).astype("float32")
                if self._index is not None:  # faiss path
                    D, I = self._index.search(q_emb, k)  # type: ignore
                    indices = [int(i) for i in I[0] if i >= 0]
                else:  # pure numpy cosine similarity
                    scores = (self._embeddings @ q_emb[0]).astype("float32")
                    if scores.size == 0:
                        return []
                    topk = min(k, scores.shape[0])
                    indices = np.argpartition(-scores, topk - 1)[:topk]
                    indices = indices[np.argsort(-scores[indices])].tolist()
            else:
                return []
            
            results: List[Dict[str, str]] = []
            seen = set()
            for idx in indices:
                if idx in seen or idx >= len(self._chunks):
                    continue
                seen.add(idx)
                chunk = self._chunks[idx]
                source = Path(chunk.doc_path).name
                results.append({"text": chunk.text, "source": source})
            
            backend_type = "bm25" if self._model == "bm25" else ("tfidf" if hasattr(self._model, 'transform') else ("faiss" if self._index else "numpy"))
            logger.info("RAG retrieval k=%d hits=%s backend=%s", k, [r['source'] for r in results], backend_type)
            return results
            
        except Exception as e:  # noqa: BLE001
            logger.warning("Retrieval failed: %s", e)
            return []

    def hybrid_retrieve(self, query: str, k: int = 3) -> List[Dict[str, str]]:
        """Minimal RRF hybrid retrieval combining BM25 and TF-IDF."""
        if not query or not query.strip():
            return []
        
        # Get candidates from both methods
        candidates = {}
        
        # Try BM25 first
        if hasattr(self, '_bm25_index') and self._model == "bm25":
            try:
                bm25_scores = self._bm25_index.get_scores(query.lower().split())
                for i, score in enumerate(bm25_scores):
                    if score > 0:
                        candidates[i] = candidates.get(i, 0) + 1 / (60 + score)
            except Exception as e:  # noqa: BLE001
                logger.warning("BM25 scoring failed: %s", e)
        
        # Try TF-IDF if available
        if hasattr(self, '_model') and hasattr(self._model, 'transform') and self._embeddings is not None:
            try:
                q_vec = self._model.transform([query])
                tfidf_scores = cosine_similarity(q_vec, self._embeddings).flatten()
                for i, score in enumerate(tfidf_scores):
                    if score > 0:
                        candidates[i] = candidates.get(i, 0) + 1 / (60 + score)
            except Exception as e:  # noqa: BLE001
                logger.warning("TF-IDF scoring failed: %s", e)
        
        # Fallback to keyword if no candidates
        if not candidates:
            return self._keyword_fallback(query, k)
        
        # Sort by combined score and return top k
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        results = []
        seen = set()
        
        for idx, _ in sorted_candidates[:k * 2]:  # Get more candidates initially
            if idx in seen or idx >= len(self._chunks):
                continue
            seen.add(idx)
            chunk = self._chunks[idx]
            source = Path(chunk.doc_path).name
            results.append({"text": chunk.text, "source": source})
            if len(results) >= k:
                break
        
        logger.info("Hybrid RRF retrieval k=%d hits=%s", k, [r['source'] for r in results])
        return results

    def _keyword_fallback(self, query: str, k: int) -> List[Dict[str, str]]:
        q_terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
        if not q_terms or not self._chunks:
            return []
        scored = []
        for i, c in enumerate(self._chunks):
            text = c.text.lower()
            score = sum(text.count(t) for t in q_terms)
            if score:
                scored.append((score, i))
        scored.sort(reverse=True)
        results = []
        for _, i in scored[:k]:
            ch = self._chunks[i]
            results.append({"text": ch.text, "source": Path(ch.doc_path).name})
        return results

__all__ = ["RAGIndex"]
