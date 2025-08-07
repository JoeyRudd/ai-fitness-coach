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
- **Transformers** - AI model pipeline using GPT-2 (planned upgrade to Phi-3)
- **Sentence Transformers** - For RAG implementation (coming soon)
- **FAISS** - Vector search for knowledge base retrieval (coming soon)

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
│   ├── main.py              # FastAPI application
│   └── pyproject.toml       # Python dependencies and config
├── frontend/
│   ├── src/
│   │   ├── App.vue          # Main application component
│   │   ├── components/      # Vue components
│   │   └── main.js          # Application entry point
│   ├── package.json         # Node.js dependencies
│   └── vite.config.ts       # Vite configuration
├── knowledge_base/          # Fitness knowledge content (for RAG)
│   ├── 01_training_frequency.md
│   ├── 02_training_intensity.md
│   └── 03_optimal_nutrition.md
└── rules.md                 # Development guidelines
```

## Target User

Designed specifically for beginners (like a 45-year-old starting their fitness journey) who need:
- Simple, encouraging language
- Safety-first recommendations
- Clear, actionable steps
- No overwhelming technical jargon

