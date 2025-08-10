# AI Fitness Coach

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
- **Sentence Transformers** + **FAISS** (planned) - RAG retrieval

### Frontend
- **Vue 3** - Progressive JavaScript framework with Composition API
- **Vite** - Fast build tool and development server
- **TailwindCSS** - Utility-first CSS framework
- **Axios** - HTTP client for API communication
- **TypeScript** - Type-safe JavaScript

## Project Structure

```
ai-fitness-coach/
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
| VITE_API_BASE | frontend | http://localhost:8000/api/v1 | Base URL the frontend uses for API calls. Must include version prefix. |

## Architecture Overview

- API Layer: FastAPI app (`backend/app/main.py`) mounting versioned routers (`api/v1/endpoints/chat.py`). Provides `/api/v1/chat` (primary) and `/api/v1/chat2` (legacy) plus health checks.
- Models: Pydantic data models in `models/chat.py` standardize message, profile, and response payloads.
- Services Layer:
  - `rag_service.RAGService`: Orchestrates intent detection (TDEE vs general), profile extraction, recall requests, TDEE calculation, lightweight RAG grounding, and LLM call / fallback.
  - `profile_logic.py`: Pure, unit-testable parsing + computation utilities (fact extraction, TDEE math, recall detection).
  - `gemini_client.py`: Thin Gemini SDK wrapper with lazy init, prompt sanitization, and safe fallback when key/model unavailable.
  - `rag_index.py`: Placeholder RAG index that loads markdown docs; future plan to build embeddings (Sentence Transformers) + FAISS vector search. Currently returns no retrievals (graceful no-op) until implemented.
- Knowledge Base: Markdown sources in `knowledge_base/` used for future grounding (currently loaded, not yet vectorized).
- Fallback Logic: When LLM unavailable (missing key or SDK failure) deterministic short supportive responses are generated for general queries; TDEE path still functions using local heuristics.

## Testing

Run tests from within the `backend/` directory (not the repo root):

```
cd backend
pytest -q
```

