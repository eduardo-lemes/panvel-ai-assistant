# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# ── Runtime ───────────────────────────────────────────────────────────────────
EXPOSE 8000

# Entrypoint: run ingest if vector store is missing, then start API
CMD ["sh", "-c", "\
  if [ ! -d '.vector_store' ] || [ -z \"$(ls -A .vector_store 2>/dev/null)\" ]; then \
    echo '>>> Vector store not found. Running ingestion...' && \
    python scripts/ingest_bulas.py; \
  fi && \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 \
"]
