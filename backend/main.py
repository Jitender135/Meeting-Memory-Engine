"""
main.py — FastAPI application exposing the Meeting Memory Engine pipeline
          as a production-ready REST API.

Endpoints:
    GET  /health        — liveness check
    GET  /meetings      — list all indexed meetings
    POST /ingest        — ingest all transcripts into ChromaDB
    POST /query         — ask a question, get a cited answer
    POST /action-items  — extract structured action items
    POST /evaluate      — evaluate RAG response quality
    POST /chat          — multi-turn conversational query

Production features:
    - API key authentication on all pipeline endpoints
    - Rate limiting (10 req/min per IP)
    - Structured logging via loguru
    - CORS middleware
    - Pydantic validation on all request/response schemas
"""

import os
import chromadb

from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Request, Depends, UploadFile, File, Form
from typing import Optional as OptionalType
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi import Security

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger

from pipeline.ingest           import ingest_all, DATA_PATH, CHROMA_PATH
from pipeline.experiment_tracker import log_rag_query
from pipeline.transcriber import transcribe_audio, save_transcript, SUPPORTED_AUDIO_FORMATS
from pipeline.retriever  import query as rag_query, extract_action_items, conversational_query, get_meeting_summary
from pipeline.evaluator import evaluate_pipeline

from models import (
    QueryRequest,
    QueryResponse,
    SourceDocument,
    IngestResponse,
    MeetingsResponse,
    MeetingMeta,
    HealthResponse,
    ActionItem,
    ActionItemsRequest,
    ActionItemsResponse,
    EvalScore,
    EvaluationResponse,
    EvaluateRequest,
    ConversationTurn,
    ConversationalQueryRequest,
    TranscribeResponse,
    MeetingSummaryResponse,
)

# ── Environment ───────────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Logging ───────────────────────────────────────────────────────
logs_dir = Path(__file__).resolve().parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)
logger.add(
    str(logs_dir / "app.log"),
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)

# ── Auth ──────────────────────────────────────────────────────────
APP_API_KEY    = os.getenv("APP_API_KEY", "dev-key-change-in-prod")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(key: str = Security(api_key_header)):
    if key != APP_API_KEY:
        logger.warning(f"Unauthorized request — invalid API key: {key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass it as X-API-Key header.",
        )

# ── Rate limiter ──────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Lifespan ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        client.get_collection("meeting_transcripts")
        logger.info("ChromaDB collection found. Pipeline ready.")
        print("✅ ChromaDB collection found. Pipeline ready.")
    except Exception:
        logger.warning("ChromaDB collection not found. Auto-ingesting...")
        print("⚠️  ChromaDB collection not found. Auto-ingesting on startup...")
        try:
            from pipeline.ingest import ingest_all, DATA_PATH
            result = ingest_all(DATA_PATH)
            logger.info(f"Auto-ingest complete: {result}")
            print(f"✅ Auto-ingest complete: {result['files']} files, {result['chunks']} chunks")
        except Exception as e:
            logger.error(f"Auto-ingest failed: {e}")
            print(f"❌ Auto-ingest failed: {e}")
    yield


# ── App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Meeting Memory Engine",
    description=(
        "A Temporal RAG pipeline that lets you query past meeting transcripts "
        "using natural language. Built with LangChain, ChromaDB, Groq (Llama 3.1), "
        "and FastAPI."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
# GET /health  — no auth, no rate limit (monitoring tools need this)
# ─────────────────────────────────────────────────────────────────
@app.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """Liveness check. Reports pipeline status."""
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
    dependencies=[Depends(verify_api_key)],
    tags=["Meetings"],
)
@limiter.limit("30/minute")
def list_meetings(request: Request) -> MeetingsResponse:
    """Returns metadata for every indexed meeting."""
    logger.info("GET /meetings")
    try:
        client     = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection("meeting_transcripts")
        results    = collection.get(include=["metadatas"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ChromaDB collection not found. Call POST /ingest first.",
        )

    seen = set()
    meetings = []
    for meta in results["metadatas"]:
        src = meta.get("source_file", "")
        if src not in seen:
            seen.add(src)
            meetings.append(MeetingMeta(
                title=meta.get("title", "Unknown"),
                date=meta.get("meeting_date", "Unknown"),
                source_file=src,
            ))

    meetings.sort(key=lambda m: m.date)
    return MeetingsResponse(total=len(meetings), meetings=meetings)


# ─────────────────────────────────────────────────────────────────
# POST /ingest
# ─────────────────────────────────────────────────────────────────
@app.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
    tags=["Pipeline"],
)
@limiter.limit("5/minute")
def ingest_transcripts(request: Request) -> IngestResponse:
    """Ingest all transcripts from data/ into ChromaDB."""
    logger.info("POST /ingest triggered")
    result = ingest_all(DATA_PATH)

    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result["message"],
        )

    logger.info(f"Ingest complete — {result['files']} files, {result['chunks']} chunks")
    return IngestResponse(**result)


# ─────────────────────────────────────────────────────────────────
# POST /query
# ─────────────────────────────────────────────────────────────────
@app.post(
    "/query",
    response_model=QueryResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["Pipeline"],
)
@limiter.limit("10/minute")
def query_meetings(request: Request, body: QueryRequest) -> QueryResponse:
    """Core RAG endpoint — hybrid search + temporal filter + cited answer."""
    logger.info(f"POST /query | question={body.question[:60]}")
    try:
        result = rag_query(
            question=body.question,
            date_from=str(body.date_from) if body.date_from else None,
            date_to=str(body.date_to)     if body.date_to   else None,
            top_k=body.top_k,
        )
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    try:
        contexts = [
            s.get("excerpt", s.get("text", s.get("content", "")))
            for s in result["sources"]
        ]
        raw_eval = evaluate_pipeline(
            question=body.question,
            answer=result["answer"],
            contexts=contexts,
        )
        eval_scores = {
            "faithfulness":      float(raw_eval.get("faithfulness",      {}).get("score", 0.0)),
            "answer_relevancy":  float(raw_eval.get("answer_relevancy",  {}).get("score", 0.0)),
            "context_precision": float(raw_eval.get("context_precision", {}).get("score", 0.0)),
        }
        log_rag_query(
            question=body.question,
            answer=result["answer"],
            sources=result["sources"],
            eval_scores=eval_scores,
            date_from=str(body.date_from) if body.date_from else None,
            date_to=str(body.date_to)     if body.date_to   else None,
            top_k=body.top_k,
        )
    except Exception as e:
        logger.warning(f"MLflow tracking skipped: {e}")

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceDocument(**s) for s in result["sources"]],
    )

# ─────────────────────────────────────────────────────────────────
# POST /action-items
# ─────────────────────────────────────────────────────────────────
@app.post(
    "/action-items",
    response_model=ActionItemsResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["Pipeline"],
)
@limiter.limit("10/minute")
def get_action_items(request: Request, body: ActionItemsRequest) -> ActionItemsResponse:
    """Extract structured action items from relevant meeting chunks."""
    logger.info(f"POST /action-items | question={body.question[:60]}")
    try:
        result = extract_action_items(
            question=body.question,
            date_from=str(body.date_from) if body.date_from else None,
            date_to=str(body.date_to)     if body.date_to   else None,
        )
    except Exception as e:
        logger.error(f"Action item extraction error: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction error: {str(e)}")

    return ActionItemsResponse(
        action_items=[ActionItem(**item) for item in result["action_items"]],
        sources=[SourceDocument(**s) for s in result["sources"]],
    )


# ─────────────────────────────────────────────────────────────────
# POST /evaluate
# ─────────────────────────────────────────────────────────────────
@app.post(
    "/evaluate",
    response_model=EvaluationResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["Pipeline"],
)
@limiter.limit("10/minute")
def evaluate_response(request: Request, body: EvaluateRequest) -> EvaluationResponse:
    """Evaluate RAG response quality using LLM-as-judge pattern."""
    logger.info(f"POST /evaluate | question={body.question[:60]}")
    try:
        result = evaluate_pipeline(
            question=body.question,
            answer=body.answer,
            contexts=body.contexts,
        )
    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation error: {str(e)}")

    return EvaluationResponse(**result)


# ─────────────────────────────────────────────────────────────────
# POST /chat
# ─────────────────────────────────────────────────────────────────
@app.post(
    "/chat",
    response_model=QueryResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["Pipeline"],
)
@limiter.limit("10/minute")
def chat(request: Request, body: ConversationalQueryRequest) -> QueryResponse:
    """Multi-turn conversational RAG with memory."""
    logger.info(f"POST /chat | question={body.question[:60]} | history_turns={len(body.history)}")
    try:
        result = conversational_query(
            question=body.question,
            history=[t.model_dump() for t in body.history],
            date_from=str(body.date_from) if body.date_from else None,
            date_to=str(body.date_to)     if body.date_to   else None,
            top_k=body.top_k,
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

    try:
        contexts = [
            s.get("excerpt", s.get("text", s.get("content", "")))
            for s in result["sources"]
        ]
        raw_eval = evaluate_pipeline(
            question=body.question,
            answer=result["answer"],
            contexts=contexts,
        )
        eval_scores = {
            "faithfulness":      float(raw_eval.get("faithfulness",      {}).get("score", 0.0)),
            "answer_relevancy":  float(raw_eval.get("answer_relevancy",  {}).get("score", 0.0)),
            "context_precision": float(raw_eval.get("context_precision", {}).get("score", 0.0)),
        }
        log_rag_query(
            question=body.question,
            answer=result["answer"],
            sources=result["sources"],
            eval_scores=eval_scores,
            date_from=str(body.date_from) if body.date_from else None,
            date_to=str(body.date_to)     if body.date_to   else None,
            top_k=body.top_k,
        )
    except Exception as e:
        logger.warning(f"MLflow tracking skipped: {e}")

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceDocument(**s) for s in result["sources"]],
    )

# ─────────────────────────────────────────────────────────────────
# POST /transcribe
# ─────────────────────────────────────────────────────────────────
@app.post(
    "/transcribe",
    response_model=TranscribeResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["Pipeline"],
)
@limiter.limit("5/minute")
def transcribe_meeting(
    request: Request,
    file: UploadFile = File(...),
    meeting_title: str = Form("Recorded Meeting"),
    meeting_date: OptionalType[str] = Form(None),
    auto_ingest: bool = Form(True),
) -> TranscribeResponse:
    """
    Upload an audio recording of a meeting — transcribes it using
    Groq Whisper, saves it as a transcript, and optionally auto-ingests
    into ChromaDB.

    Supported formats: mp3, wav, m4a, flac, ogg, webm

    Why this completes the product story:
        Without this, users need pre-made text transcripts.
        With this, the flow becomes: record meeting -> upload audio
        -> ask questions. End-to-end, no manual transcription step.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio format '{suffix}'. "
                   f"Supported: {', '.join(SUPPORTED_AUDIO_FORMATS)}",
        )

    logger.info(f"POST /transcribe | file={file.filename} | title={meeting_title}")

    try:
        audio_bytes = file.file.read()
        transcript  = transcribe_audio(audio_bytes, file.filename)

        save_result = save_transcript(
            transcript_text=transcript,
            meeting_title=meeting_title,
            meeting_date=meeting_date,
        )

        chunks_added = 0
        ingested     = False
        if auto_ingest:
            ingest_result = ingest_all(DATA_PATH)
            if ingest_result["status"] == "success":
                ingested     = True
                chunks_added = ingest_result["chunks"]

        logger.info(f"Transcription complete | filename={save_result['filename']} | ingested={ingested}")

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription error: {str(e)}",
        )

    return TranscribeResponse(
        status="success",
        filename=save_result["filename"],
        transcript=transcript,
        ingested=ingested,
        chunks_added=chunks_added,
    )


# ─────────────────────────────────────────────────────────────────
# GET /summary/{meeting_date}
# ─────────────────────────────────────────────────────────────────
@app.get(
    "/summary/{meeting_date}",
    response_model=MeetingSummaryResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["Pipeline"],
)
@limiter.limit("10/minute")
def meeting_summary(request: Request, meeting_date: str) -> MeetingSummaryResponse:
    """
    Generate a structured summary for a specific meeting by date.

    Path parameter: meeting_date in YYYY-MM-DD format.

    Returns key decisions, action items, and open questions
    extracted from that meeting's full transcript.
    """
    logger.info(f"GET /summary/{meeting_date}")
    try:
        result = get_meeting_summary(meeting_date)
    except Exception as e:
        logger.error(f"Summary error: {e}")
        raise HTTPException(status_code=500, detail=f"Summary error: {str(e)}")

    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "Meeting not found."))

    return MeetingSummaryResponse(**result)