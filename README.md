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
- **NEW: Enhanced workout split guidance** - Specific schedules and exercise recommendations
- **NEW: BM25 retrieval support** - Better handling of short queries and workout-related questions

## Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **Google Gemini (google-generativeai)** - LLM for responses
- **Hybrid RAG System**:
  - **BM25 (rank-bm25)** - Primary retrieval method for short queries and workout questions
  - **TF-IDF (scikit-learn)** - Fallback for chunk embedding and retrieval (fast, lightweight)
  - **Sentence Transformers** - Advanced semantic search when available
- All searching happens quickly and locally with intelligent fallbacks

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
│   ├── 01_training_frequency.md # Workout splits, training frequency, schedules
│   ├── 02_training_intensity.md
│   ├── 03_optimal_nutrition.md
│   ├── 04_strength_training_basics.md # Beginner exercises, workout organization
│   ├── 05_cardio_fundamentals.md
│   ├── 06_recovery_rest.md
│   ├── 07_goal_setting_motivation.md
│   └── 08_faq.md
└── rules.md                     # Development guidelines
```

## Target User

Designed specifically for beginners (like a 45-year-old starting their fitness journey) who need:
- Simple, encouraging language
- Safety-first recommendations
- Clear, actionable steps
- No overwhelming technical jargon
- **Specific workout guidance** - Full body splits, schedules, exercise recommendations

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
  - `rag_service.RAGService`: Intent detection (TDEE vs general), profile extraction, recall, TDEE calculation, RAG grounding, LLM call / fallback, **workout split detection and fallback responses**.
  - `rag_index.RAGIndex`: Loads markdown, chunks, and uses **BM25 as primary retrieval method** for better short query handling. Falls back to TF-IDF (scikit-learn) or sentence-transformers (MiniLM) with NumPy/FAISS for similarity.
  - `profile_logic.py`: Fact extraction & calculations.
  - `gemini_client.py`: Gemini SDK wrapper with simple generation call.
- **Knowledge Base:** Local markdown sources in `knowledge_base/` ground general fitness answers with **comprehensive workout split information**.
- **Fallback Logic:** If LLM not configured, deterministic supportive responses with **specific workout split guidance**.

## RAG Retrieval Flow
1. Load markdown docs from `knowledge_base/` (recursive).
2. Chunk into ~800 char windows with overlap.
3. **Primary: BM25 indexing** for optimal short query and workout question handling.
4. **Fallback 1:** TF-IDF (scikit-learn) for chunk embedding and retrieval.
5. **Fallback 2:** Sentence transformers (MiniLM) with normalization.
6. Store chunk vectors in memory (no external DB).
7. On user query (non-TDEE):
   - **BM25 retrieval** for workout split questions and short queries
   - **Hybrid retrieval** combining multiple methods for optimal results
   - **Workout split detection** with specialized fallback responses
8. Inject context block into prompt with anti-hallucination guidance.
9. **Enhanced fallback:** Deterministic supportive responses with specific workout split schedules and exercise recommendations.

## New Features

### Enhanced Workout Split Guidance
- **Full Body Split**: Monday/Wednesday/Friday schedule with rest days
- **Upper/Lower Split**: 4-day training schedule for intermediate beginners
- **Push/Pull/Legs**: 6-day advanced split for experienced lifters
- **Specific Exercise Recommendations**: leg press, chest press, lat pulldown, shoulder press
- **Progression Paths**: Clear guidance on when to advance to more complex splits

### BM25 Retrieval System
- **Better Short Query Handling**: Improved retrieval for workout-related questions
- **Hybrid Search**: Combines BM25 with traditional methods for optimal results
- **Workout Split Detection**: Automatically identifies and responds to workout split questions
- **Intelligent Fallbacks**: Provides helpful guidance even when RAG retrieval doesn't find optimal content

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

## Recent Updates

- **Workout Split Enhancements**: Added comprehensive workout split guidance with specific schedules and exercise recommendations
- **BM25 Integration**: Implemented BM25 retrieval for better short query handling
- **Improved RAG Service**: Enhanced prompt construction and fallback responses for workout questions
- **Knowledge Base Expansion**: Added detailed workout split information and training frequency guidance



