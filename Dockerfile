# ── Base image ────────────────────────────────────────────────────
FROM python:3.11-slim

# ── Set working directory ─────────────────────────────────────────
WORKDIR /app

# ── Install system dependencies ───────────────────────────────────
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Copy and install Python dependencies ─────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir \
    langchain-groq \
    langchain-huggingface \
    sentence-transformers \
    slowapi \
    loguru \
    pymupdf \
    python-docx \
    rank-bm25

# ── Copy application code ─────────────────────────────────────────
COPY backend/ ./backend/
COPY data/    ./data/

# ── Create directories ────────────────────────────────────────────
RUN mkdir -p logs chroma_db

# ── Expose port ───────────────────────────────────────────────────
EXPOSE 8000

# ── Start FastAPI ─────────────────────────────────────────────────
WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]