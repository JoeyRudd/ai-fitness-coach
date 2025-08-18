# Hypertrofit

[![CI/CD Pipeline](https://github.com/JoeyRudd/ai-fitness-coach/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/JoeyRudd/ai-fitness-coach/actions)

<!-- Test commit for Railway deployment -->

A simple, user-friendly AI-powered fitness and nutrition coach application designed for beginners. The AI provides encouraging, safety-first advice using plain English explanations.

## Features

- AI-powered fitness and nutrition advice
- Beginner-friendly interface designed for easy use
- Interactive chat interface with real-time responses
- Safety-first approach with doctor consultation recommendations
- Responsive design with TailwindCSS

## Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **Google Gemini (google-generativeai)** - LLM for responses
- **TF-IDF (scikit-learn)** is the default for chunk embedding and retrieval (fast, lightweight, no external dependencies).
- If the simple word-matching method (TF-IDF) isn't available, the system tries a more advanced way to understand meaning. All searching happens quickly and locally. Extra tools are only used if your knowledge base gets very large (over 5,000 pieces of information).

### Frontend
- **Vue 3** - Progressive JavaScript framework with Composition API
- **Vite** - Fast build tool and development server
- **TailwindCSS** - Utility-first CSS framework
- **Axios** - HTTP client for API communication
- **TypeScript** - Type-safe JavaScript

## Project Structure

```
hypertrofit/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application (single app instance)
│   │   ├── api/
│   │   │   └── v1/endpoints/    # Versioned API routers
│   │   ├── core/                # Config / settings
│   │   ├── models/              # Pydantic models (may be split later into schemas/)
│   │   └── services/            # Business / RAG logic
│   └── pyproject.toml           # Python dependencies and config
├── frontend/
│   ├── src/
│   │   ├── App.vue              # Main application component
│   │   ├── components/          # Vue components
│   │   └── main.js              # Frontend entry point
│   ├── package.json             # Node.js dependencies
│   └── vite.config.ts           # Vite configuration
├── knowledge_base/              # Fitness knowledge content (for RAG)
│   ├── 01_training_frequency.md
│   ├── 02_training_intensity.md
│   └── 03_optimal_nutrition.md
└── rules.md                     # Development guidelines
```

## Target User

Designed specifically for beginners (like a 45-year-old starting their fitness journey) who need:
- Simple, encouraging language
- Safety-first recommendations
- Clear, actionable steps
- No overwhelming technical jargon

## Environment Variables

| Name | Scope | Default | Description |
|------|-------|---------|-------------|
| GEMINI_API_KEY | backend | (empty) | Google Generative AI API key. If missing, system returns deterministic fallback instead of failing. |
| GEMINI_MODEL / GEMINI_MODEL_NAME | backend | gemini-1.5-flash | Model name. `gemini_client` reads `GEMINI_MODEL`; settings class uses `GEMINI_MODEL_NAME`. Either works. |
| ALLOWED_ORIGINS | backend | http://localhost:5173 | Comma-separated list for CORS (frontend dev origin). |
| KNOWLEDGE_BASE_PATH | backend | knowledge_base | Override location of markdown knowledge base. |
| EMBEDDING_MODEL_NAME | backend | all-MiniLM-L6-v2 | Sentence transformer model used for embeddings. |
| MAX_RETRIEVAL_CHUNKS | backend | 3 | How many context chunks to inject into prompt. |
| VITE_API_BASE | frontend | http://localhost:8000/api/v1 | Base URL the frontend uses for API calls. Must include version prefix. |

## Architecture Overview

- **API Layer:** FastAPI app (`backend/app/main.py`) mounting versioned routers (`api/v1/endpoints/chat.py`).
- **Models:** Pydantic data models in `models/chat.py` standardize message, profile, and response payloads.
- **Services Layer:**
  - `rag_service.RAGService`: Intent detection (TDEE vs general), profile extraction, recall, TDEE calculation, RAG grounding, LLM call / fallback.
  - `rag_index.RAGIndex`: Loads markdown, chunks, and by default uses TF-IDF (scikit-learn) for chunk embedding and retrieval. If unavailable, falls back to sentence-transformers (MiniLM) with NumPy or FAISS for similarity (all in memory, no external DB by default).
  - `profile_logic.py`: Fact extraction & calculations.
  - `gemini_client.py`: Gemini SDK wrapper with simple generation call.
- **Knowledge Base:** Local markdown sources in `knowledge_base/` ground general fitness answers.
- **Fallback Logic:** If LLM not configured, deterministic supportive responses.

## RAG Retrieval Flow
1. Load markdown docs from `knowledge_base/` (recursive).
2. Chunk into ~800 char windows with overlap.
3. By default, embed chunks using TF-IDF (scikit-learn). If unavailable, use sentence-transformers (MiniLM) with normalization.
4. Store chunk vectors in memory (TF-IDF matrix or embedding matrix; no FAISS, no external DB).
5. On user query (non-TDEE):
  - If TF-IDF is available, embed query and compute cosine similarity with chunk TF-IDF vectors.
  - If not, use sentence-transformers to embed and compare with chunk embeddings (NumPy or FAISS).
6. Select top k chunks.
7. Inject context block into prompt (sources + truncated text) with anti-hallucination guidance ("If you don't know, say so").
8. Fallback: If Gemini is not configured, return deterministic supportive responses.

## Local Development

Backend:
```
make install
make backend
```
Frontend:
```
cd frontend
npm install
npm run dev
```

## Testing

```
make test
```



