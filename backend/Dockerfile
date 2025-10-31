# Backend Dockerfile for AI Fitness Coach
# Multi-stage build for smaller final image
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --user -r /app/requirements.txt

# Production stage
FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy backend source and knowledge base
COPY backend /app/backend
COPY knowledge_base /app/knowledge_base

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Environment variables (override in deploy)
ENV ALLOWED_ORIGINS="http://localhost:5173" \
    KNOWLEDGE_BASE_PATH="knowledge_base" \
    OPENROUTER_MODEL="deepseek/deepseek-chat"

# Start the API
# --app-dir backend ensures module imports resolve from backend/app
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir backend"]
