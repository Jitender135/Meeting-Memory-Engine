"""
models.py — Pydantic schemas for all FastAPI request and response payloads.

Why Pydantic:
- Automatic request validation — FastAPI rejects malformed requests before
  they ever touch the pipeline
- Auto-generated API docs at /docs — zero extra work
- Type safety across the entire backend
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date


# ─────────────────────────────────────────────
# REQUEST SCHEMAS
# ─────────────────────────────────────────────

class QueryRequest(BaseModel):
    """
    Payload for POST /query
    
    date_from / date_to are optional — when omitted, retrieval
    searches across all meetings (no temporal filter applied).
    """
    question: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="The question to ask against the meeting transcripts.",
        examples=["What did we decide about the mobile app launch?"],
    )
    date_from: Optional[date] = Field(
        default=None,
        description="Filter meetings on or after this date (YYYY-MM-DD).",
        examples=["2024-01-01"],
    )
    date_to: Optional[date] = Field(
        default=None,
        description="Filter meetings on or before this date (YYYY-MM-DD).",
        examples=["2024-06-30"],
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of transcript chunks to retrieve. Default 3.",
    )

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question must not be blank or whitespace only.")
        return v.strip()

    @field_validator("date_to")
    @classmethod
    def date_range_must_be_valid(cls, date_to, info) -> Optional[date]:
        date_from = info.data.get("date_from")
        if date_from and date_to and date_to < date_from:
            raise ValueError("date_to must be on or after date_from.")
        return date_to


# ─────────────────────────────────────────────
# RESPONSE SCHEMAS
# ─────────────────────────────────────────────

class SourceDocument(BaseModel):
    title:   str   = Field(description="Meeting title extracted from transcript.")
    date:    str   = Field(description="Meeting date in YYYY-MM-DD format.")
    score:   float = Field(description="Cosine similarity score (0–1). Higher = more relevant.")
    excerpt: str   = Field(default="", description="Raw chunk text used for evaluation.")


class QueryResponse(BaseModel):
    """
    Response payload for POST /query
    """
    answer:  str                  = Field(description="LLM-generated answer grounded in retrieved chunks.")
    sources: list[SourceDocument] = Field(description="Ranked list of source meetings used to generate the answer.")


class IngestResponse(BaseModel):
    """
    Response payload for POST /ingest
    """
    status:     str = Field(description="'success' or 'error'")
    files:      int = Field(description="Number of transcript files ingested.")
    chunks:     int = Field(description="Total number of chunks stored in ChromaDB.")
    collection: str = Field(description="ChromaDB collection name.")


class MeetingMeta(BaseModel):
    """
    Metadata for a single indexed meeting.
    Returned by GET /meetings
    """
    title:       str = Field(description="Meeting title.")
    date:        str = Field(description="Meeting date.")
    source_file: str = Field(description="Original transcript filename.")


class MeetingsResponse(BaseModel):
    """
    Response payload for GET /meetings
    """
    total:    int              = Field(description="Total number of indexed meetings.")
    meetings: list[MeetingMeta] = Field(description="List of all indexed meeting metadata.")


class HealthResponse(BaseModel):
    """
    Response payload for GET /health
    """
    status:   str = Field(description="'ok' if service is running.")
    pipeline: str = Field(description="'ready' if ChromaDB collection exists.")

class ActionItem(BaseModel):
    """A single extracted action item from retrieved meeting chunks."""
    owner:  str = Field(description="Person responsible for the action item.")
    task:   str = Field(description="What needs to be done.")
    due:    str = Field(description="Due date or deadline. 'Not specified' if absent.")
    meeting: str = Field(description="Meeting title this action item came from.")
    date:   str = Field(description="Meeting date.")


class ActionItemsRequest(BaseModel):
    """Payload for POST /action-items"""
    question: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Topic or question to extract action items for.",
        examples=["What action items were assigned in the engineering sprint?"],
    )
    date_from: Optional[date] = Field(default=None)
    date_to:   Optional[date] = Field(default=None)


class ActionItemsResponse(BaseModel):
    """Response payload for POST /action-items"""
    action_items: list[ActionItem] = Field(description="Extracted action items.")
    sources:      list[SourceDocument] = Field(description="Meetings searched.")

class EvalScore(BaseModel):
    score:  float = Field(description="Score between 0 and 1.")
    reason: str   = Field(description="One sentence explanation.")


class EvaluationResponse(BaseModel):
    status:            str       = Field(description="'success' or 'error'")
    overall:           float     = Field(description="Weighted overall score (0-1).")
    faithfulness:      EvalScore = Field(description="Are claims grounded in context?")
    answer_relevancy:  EvalScore = Field(description="Does answer address the question?")
    context_precision: EvalScore = Field(description="Are retrieved chunks relevant?")


class EvaluateRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    answer:   str = Field(..., min_length=5)
    contexts: list[str] = Field(..., description="List of retrieved chunk texts.")