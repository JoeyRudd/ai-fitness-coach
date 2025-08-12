# Ultra-optimized build with ML libraries but aggressive size reduction
FROM python:3.11-slim as builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TORCH_HOME=/tmp/torch \
    HF_HOME=/tmp/huggingface

# Install minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies with aggressive cleanup
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + && \
    find /opt/venv -name "*.pyo" -delete && \
    find /opt/venv -name "*.so" -exec strip {} \; 2>/dev/null || true && \
    rm -rf /opt/venv/lib/python*/site-packages/*/tests && \
    rm -rf /opt/venv/lib/python*/site-packages/*/test && \
    rm -rf /opt/venv/lib/python*/site-packages/torch/test && \
    rm -rf /opt/venv/lib/python*/site-packages/torch/include && \
    rm -rf /opt/venv/lib/python*/site-packages/torch/share && \
    rm -rf /opt/venv/lib/python*/site-packages/transformers/tests && \
    rm -rf /opt/venv/lib/python*/site-packages/sentence_transformers/examples && \
    find /opt/venv -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Final stage - ultra minimal runtime
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    TRANSFORMERS_CACHE=/tmp/transformers \
    HF_HOME=/tmp/huggingface \
    TORCH_HOME=/tmp/torch

WORKDIR /app

# Copy virtual environment and source code
COPY --from=builder /opt/venv /opt/venv
COPY backend /app/backend
COPY knowledge_base /app/knowledge_base

# Create non-root user and set permissions
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Environment variables
ENV ALLOWED_ORIGINS="http://localhost:5173" \
    KNOWLEDGE_BASE_PATH="knowledge_base" \
    GEMINI_MODEL_NAME="gemini-1.5-flash"

# Start the API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
