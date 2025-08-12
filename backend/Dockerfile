# Backend Dockerfile for AI Fitness Coach
# Lightweight CPU-only image
FROM python:3.11-slim AS base

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system deps for scientific Python and building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency list and install
# Using repo root requirements.txt which pins runtime deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Copy backend source and knowledge base
COPY backend /app/backend
COPY knowledge_base /app/knowledge_base

# Create a non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# Environment variables (override in deploy)
ENV ALLOWED_ORIGINS="http://localhost:5173" \
    KNOWLEDGE_BASE_PATH="knowledge_base" \
    GEMINI_MODEL_NAME="gemini-1.5-flash"

# Start the API
# --app-dir backend ensures module imports resolve from backend/app
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir backend"]
