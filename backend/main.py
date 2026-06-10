"""
main.py — FastAPI application exposing the Meeting Memory Engine pipeline
          as a production-ready REST API.

Endpoints:
    GET  /health     — liveness check
    GET  /meetings   — list all indexed meetings
    POST /ingest     — ingest all transcripts from data/ into ChromaDB
    POST /query      — ask a question, get a cited answer

Why FastAPI:
    - Automatic OpenAPI docs at /docs (great for interviews — live demo)
    - Pydantic validation built in — bad requests never reach the pipeline
    - Async support — ready to scale if needed
"""

import os
import chromadb

from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from pipeline.ingest    import ingest_all, DATA_PATH, CHROMA_PATH
from pipeline.retriever import query as rag_query
from models import (
    QueryRequest,
    QueryResponse,
    SourceDocument,
    IngestResponse,
    MeetingsResponse,
    MeetingMeta,
    HealthResponse,
)

# ── Environment ───────────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# ── Lifespan — runs once on startup ──────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Verify ChromaDB collection exists on startup.
    Warns early if transcripts haven't been ingested yet.
    """
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        client.get_collection("meeting_transcripts")
        print("✅ ChromaDB collection found. Pipeline ready.")
    except Exception:
        print("⚠️  ChromaDB collection not found. Call POST /ingest first.")
    yield


# ── App instance ──────────────────────────────────────────────────
app = FastAPI(
    title="Meeting Memory Engine",
    description=(
        "A Temporal RAG pipeline that lets you query your past meeting "
        "transcripts using natural language. Built with LangChain, ChromaDB, "
        "Groq (Llama 3.1), and FastAPI."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS — allows Streamlit frontend to call this API ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
# GET /health
# ─────────────────────────────────────────────────────────────────
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
def health_check() -> HealthResponse:
    """
    Liveness check. Also reports whether the ChromaDB
    collection is ready to serve queries.
    """
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        client.get_collection("meeting_transcripts")
        pipeline_status = "ready"
    except Exception:
        pipeline_status = "not ingested — call POST /ingest"

    return HealthResponse(status="ok", pipeline=pipeline_status)


# ─────────────────────────────────────────────────────────────────
# GET /meetings
# ─────────────────────────────────────────────────────────────────
@app.get(
    "/meetings",
    response_model=MeetingsResponse,
    summary="List all indexed meetings",
    tags=["Meetings"],
)
def list_meetings() -> MeetingsResponse:
    """
    Returns metadata for every meeting indexed in ChromaDB.
    Useful for the frontend to show available meetings and date ranges.
    """
    try:
        client     = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection("meeting_transcripts")
        results    = collection.get(include=["metadatas"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ChromaDB collection not found. Call POST /ingest first.",
        )

    # Deduplicate by source_file — each transcript = one meeting entry
    seen     = set()
    meetings = []
    for meta in results["metadatas"]:
        src = meta.get("source_file", "")
        if src not in seen:
            seen.add(src)
            meetings.append(
                MeetingMeta(
                    title=meta.get("title", "Unknown"),
                    date=meta.get("meeting_date", "Unknown"),
                    source_file=src,
                )
            )

    # Sort by date ascending
    meetings.sort(key=lambda m: m.date)

    return MeetingsResponse(total=len(meetings), meetings=meetings)


# ─────────────────────────────────────────────────────────────────
# POST /ingest
# ─────────────────────────────────────────────────────────────────
@app.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest all transcripts into ChromaDB",
    tags=["Pipeline"],
)
def ingest_transcripts() -> IngestResponse:
    """
    Loads all .txt files from data/, chunks them, embeds with
    HuggingFace all-MiniLM-L6-v2, and stores in ChromaDB.

    Safe to call multiple times — ChromaDB upserts, so no duplicates.
    """
    result = ingest_all(DATA_PATH)

    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result["message"],
        )

    return IngestResponse(**result)


# ─────────────────────────────────────────────────────────────────
# POST /query  ← the core endpoint
# ─────────────────────────────────────────────────────────────────
@app.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a question about your meetings",
    tags=["Pipeline"],
)
def query_meetings(request: QueryRequest) -> QueryResponse:
    """
    The core RAG endpoint.

    Flow:
        1. Embed the question using all-MiniLM-L6-v2
        2. Apply optional temporal filter (date_from / date_to)
        3. Retrieve top_k most similar chunks from ChromaDB
        4. Build a cited prompt and call Groq Llama 3.1
        5. Return the answer + ranked source meetings

    The date filter is applied PRE-retrieval inside ChromaDB —
    not post-hoc by the LLM — ensuring temporal accuracy.
    """
    try:
        result = rag_query(
            question=request.question,
            date_from=str(request.date_from) if request.date_from else None,
            date_to=str(request.date_to)     if request.date_to   else None,
            top_k=request.top_k,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline error: {str(e)}",
        )

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceDocument(**s) for s in result["sources"]],
    )