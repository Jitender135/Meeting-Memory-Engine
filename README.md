# Meeting Memory Engine
![CI](https://github.com/Jitender135/Meeting-Memory-Engine/actions/workflows/ci.yml/badge.svg)

A production-ready **Temporal RAG (Retrieval-Augmented Generation)** system that lets you query past meeting transcripts using natural language — with cited, time-accurate, grounded answers.

**Live App (React):** https://meeting-memory-engine.vercel.app
**Live App (Streamlit):** https://meeting-memory-engine-n5iyrh3cmnjkvd5scvnnpn.streamlit.app
**Live API:** https://meeting-memory-engine.onrender.com/docs
**GitHub:** https://github.com/Jitender135/Meeting-Memory-Engine

> Note: Backend hosted on Render free tier. If the API is sleeping, click "Re-index transcripts" in the sidebar and wait ~30 seconds. UptimeRobot pings the server every 5 minutes to minimise this.

---

## The Problem

After months of meetings, nobody remembers what was decided, who committed to what, or when that pricing discussion happened. You dig through Slack, scan notes, and still come up empty.

**Meeting Memory Engine fixes that.**

Record or upload your meeting transcripts and ask:
- *"What did we decide about the mobile app launch?"*
- *"What action items were assigned to Rahul in Q1?"*
- *"Summarise all decisions made before the product pivot."*
- *"Who was responsible for that?"* — and follow up conversationally

Get cited, accurate answers with the meeting date and source — instantly.

---

## Architecture

```
Audio Recording (mp3/wav/m4a)        Transcripts (TXT / PDF / DOCX)
        │                                     │
        ▼                                     │
┌─────────────────────────────────┐           │
│   Groq Whisper Transcription    │           │
│   (whisper-large-v3, free API)  │           │
└───────────────┬─────────────────┘           │
                │                             │
                └──────────────┬──────────────┘
                                ▼
                ┌─────────────────────────────────┐
                │   Multi-format Document Loader  │  Supports .txt .pdf .docx
                │   + Metadata Tagger             │  Attaches meeting_date, title,
                │                                 │  participants, source_file, format
                └───────────────┬─────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────┐
                │   Text Chunker                  │  RecursiveCharacterTextSplitter
                │   chunk=500 / overlap=50        │  Splits on paragraphs → sentences → words
                └───────────────┬─────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────┐
                │   Jina AI Embeddings            │  jina-embeddings-v2-base-en
                │   (API-based, no local model)   │  <10MB RAM vs 500MB for local models
                └───────────────┬─────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────┐
                │   ChromaDB Vector Store         │  Stores vectors + raw text + metadata
                │   (persisted to disk)           │  Enables pre-retrieval date filtering
                └───────────────┬─────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────┐
                │   Hybrid Retriever              │  BM25 keyword search
                │   BM25 + Semantic + RRF         │  + Semantic vector search
                │   + Temporal Pre-filter         │  + Reciprocal Rank Fusion
                │                                 │  Date filter applied BEFORE similarity search
                └───────────────┬─────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────┐
                │   Groq — Llama 3.1 8b Instant  │  Generates cited, grounded answers
                │                                 │  temperature=0.2 for factual output
                └───────────────┬─────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────┐
                │   FastAPI REST API              │  9 endpoints, API key auth,
                │                                 │  rate limiting, structured logging
                └───────────────┬─────────────────┘
                                │
                        ┌───────┴───────┐
                        ▼               ▼
            ┌───────────────┐   ┌───────────────────┐
            │  React UI     │   │   Streamlit UI    │
            │  (Vercel)     │   │   (Streamlit      │
            │  Search+Chat  │   │    Cloud)         │
            │  Audio+Summary│   │   Backup UI       │
            │  Dark mode    │   │                   │
            └───────────────┘   └───────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| RAG Framework | LangChain | RAG orchestration — loaders, splitters, chains |
| Vector Database | ChromaDB | Stores vectors + metadata — enables date filters |
| Embeddings | Jina AI `jina-embeddings-v2-base-en` | API-based, zero RAM overhead, free tier compatible |
| Keyword Search | BM25 via rank-bm25 | Catches exact matches semantic search misses |
| LLM | Groq — Llama 3.1 8b Instant | Fast free inference, 8192 token context |
| Audio Transcription | Groq Whisper `whisper-large-v3` | Free, API-based, near-perfect quality |
| API Layer | FastAPI + Pydantic | REST endpoints, auto OpenAPI docs, request validation |
| Auth | API Key Header (X-API-Key) | Protects all pipeline endpoints |
| Rate Limiting | slowapi | Per-endpoint limits, per IP |
| Logging | loguru | Structured logs, daily rotation, 7-day retention |
| React Frontend | React + Vite + Tailwind v4 | Modern light/dark SaaS UI, deployed on Vercel |
| Streamlit Frontend | Streamlit | Backup UI, deployed on Streamlit Cloud |
| Containerisation | Docker + docker-compose | Consistent builds, deployable anywhere |
| Backend Hosting | Render | Free tier, auto-deploy on GitHub push |
| React Hosting | Vercel | Free hobby tier, auto-deploy on push |
| Streamlit Hosting | Streamlit Community Cloud | Free, auto-deploy on push |
| Uptime Monitoring | UptimeRobot | Pings /health every 5 minutes to prevent sleep |

---

## Features

### Core Pipeline
- **Temporal RAG** — pre-retrieval date filtering using ChromaDB `where` clause. "What did we decide last quarter?" only retrieves chunks from that time window — not semantically similar but temporally wrong results.
- **Hybrid Search** — BM25 keyword search + semantic vector search combined with Reciprocal Rank Fusion (RRF). Pure semantic search misses exact keyword matches (names, dates, project codes). BM25 catches those.
- **Multi-format Ingestion** — ingests `.txt`, `.pdf` (via PyMuPDF), and `.docx` (via python-docx) transcripts with structured metadata.
- **Cited Answers** — every answer includes the meeting title and date it was sourced from.

### Advanced Features
- **Audio Transcription** — upload a meeting recording (`.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.webm`) and it's transcribed via Groq Whisper, saved as a transcript, and auto-ingested. Record meeting → upload → query immediately.
- **Meeting Summaries** — per-meeting structured summary extracting key decisions, action items, and open questions. Expandable in the sidebar per meeting.
- **Action Item Extractor** — focused LLM call extracts structured action items (owner, task, due date, meeting) across all meetings. Returns as a clean table.
- **Conversational Memory** — multi-turn chat mode with stateless history pattern. Ask "Who was responsible for that?" and the LLM resolves references using conversation history.
- **Custom RAG Evaluator** — LLM-as-judge measuring Faithfulness, Answer Relevance, and Context Precision. Built custom instead of RAGAS due to LangChain 1.x dependency conflicts.
- **Auto-ingest on Startup** — if ChromaDB collection is missing on startup, the server automatically ingests all transcripts from `data/`.

### React Frontend
- **Search mode** — question input, answer with left-border accent, ranked source cards, action items table
- **Chat mode** — multi-turn conversation with message bubbles, source tags, auto-scroll
- **Audio upload** — file picker in sidebar, title/date inputs, transcribe & index in one click
- **Meeting summaries** — expandable per-meeting cards in sidebar with key decisions/action items/open questions
- **Loading skeleton** — pulsing placeholders while search is running
- **Dark mode** — pill toggle, persisted in localStorage, full dark theme

### Production Hardening
- API key authentication on all pipeline endpoints
- Rate limiting per endpoint, per IP
- Structured logging with daily rotation
- CORS middleware
- Health check endpoint
- Docker + docker-compose
- UptimeRobot monitoring every 5 minutes

---

## API Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|---|---|---|---|---|
| GET | `/health` | None | None | Liveness check + pipeline status |
| GET | `/meetings` | Required | 30/min | List all indexed meetings |
| GET | `/summary/{meeting_date}` | Required | 10/min | Structured summary per meeting |
| POST | `/ingest` | Required | 5/min | Ingest transcripts into ChromaDB |
| POST | `/query` | Required | 10/min | Ask a question, get a cited answer |
| POST | `/action-items` | Required | 10/min | Extract structured action items |
| POST | `/evaluate` | Required | 10/min | Evaluate RAG response quality |
| POST | `/chat` | Required | 10/min | Multi-turn conversational query |
| POST | `/transcribe` | Required | 5/min | Upload audio — Whisper transcription + auto-ingest |

### POST /query — Example

**Request:**
```json
{
  "question": "What did we decide about the mobile app launch?",
  "date_from": "2024-01-01",
  "date_to": "2024-06-30",
  "top_k": 3
}
```

**Headers:**
```
X-API-Key: your-api-key
Content-Type: application/json
```

**Response:**
```json
{
  "answer": "The team decided to launch on iOS first on April 5th, with Android following in 6 weeks after performance optimization. (Mobile App Launch Review | 2024-03-22)",
  "sources": [
    { "title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.0323 },
    { "title": "Q1 Product Planning", "date": "2024-01-15", "score": 0.0315 }
  ]
}
```

### GET /summary/{meeting_date} — Example

**Response:**
```json
{
  "status": "success",
  "title": "Q1 Product Planning",
  "date": "2024-01-15",
  "key_decisions": [
    "Prioritize onboarding flow redesign in Q1",
    "Delay mobile app launch from February to April"
  ],
  "action_items": [
    "Amit: Onboarding prototype by Feb 10",
    "Sarah: Retention dashboard by Jan 22"
  ],
  "open_questions": []
}
```

### POST /transcribe — Example

**Request (multipart/form-data):**
```
file: meeting_recording.mp3
meeting_title: "Q4 Planning Sync"
meeting_date: "2024-12-05"
auto_ingest: true
```

**Response:**
```json
{
  "status": "success",
  "filename": "meeting_2024_12_05.txt",
  "transcript": "Okay team, let's go over today's action items...",
  "ingested": true,
  "chunks_added": 13
}
```

---

## Key Design Decisions

**Why `chunk_size=500` with `overlap=50`?**
500 tokens captures one complete meeting topic without bleeding into the next. The 50-token overlap prevents decisions from being split at chunk edges.

**Why ChromaDB over FAISS?**
ChromaDB stores vectors and metadata together — enables pre-retrieval date filtering. FAISS is vectors-only. Trade-off: ChromaDB suits ~10k chunks; at 100k+ migrate to Pinecone or Qdrant.

**Why temporal pre-retrieval filtering?**
The LLM only sees what the retriever hands it. Without date filtering, "what did we decide last quarter?" returns semantically similar chunks from any time period. Filtering before similarity search guarantees time-accurate context.

**Why hybrid search?**
Pure semantic search misses exact keyword matches. BM25 catches names, project codes, specific dates. Combining both with RRF gives higher precision than either alone.

**Why FastAPI over calling the pipeline directly from Streamlit?**
A pipeline inside Streamlit is a demo. A pipeline behind a REST endpoint is a service — any consumer (Slack bot, mobile app, cron job) can call `/query` without touching AI code.

**Why Jina AI embeddings instead of local HuggingFace?**
Local HuggingFace models require 400-500MB RAM. Render free tier caps at 512MB — causes OOM crashes. Jina API embeddings use less than 10MB RAM.

**Why Groq Whisper for audio transcription?**
Free using the same API key as the LLM. whisper-large-v3 offers near-perfect transcription for clear speech — avoids RAM overhead of local Whisper models.

**Why custom RAG evaluator instead of RAGAS?**
RAGAS requires LangChain 0.2.x which conflicts with our 1.x stack. LLM-as-judge gives identical methodology with zero dependency risk.

**Why stateless conversational memory?**
Stateful server-side memory breaks horizontal scaling. Passing history from the client on every request keeps the backend stateless — correct REST pattern.

**Why React + Vite + Tailwind v4 for the frontend?**
Tailwind v4 uses CSS variables natively — perfect for dark mode without JavaScript class juggling. Vite gives instant HMR. React gives component reusability across Search, Chat, and Audio upload flows.

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Jitender135/Meeting-Memory-Engine.git
cd Meeting-Memory-Engine
```

### 2. Create and activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
JINA_API_KEY=your_jina_api_key_here
APP_API_KEY=your_secret_key_here
```

| Key | Where to get it | Cost |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | Free |
| `JINA_API_KEY` | [jina.ai](https://jina.ai) | Free — 1M tokens/month |
| `APP_API_KEY` | Any string you choose | — |

### 5. Add meeting transcripts

Drop files into `data/`. Supported: `.txt`, `.pdf`, `.docx`

Required filename format: `meeting_YYYY_MM_DD.ext`

Or upload audio directly through the React UI — transcribed and ingested automatically.

### 6. Ingest transcripts

```bash
cd backend
python pipeline/ingest.py
```

### 7. Start the FastAPI backend

```bash
uvicorn main:app --reload --port 8000
```

Docs: **http://localhost:8000/docs**

### 8. Start the React frontend

```bash
cd frontend-react
npm install
npm run dev
```

UI: **http://localhost:5173**

### 9. (Optional) Start the Streamlit frontend

```bash
cd frontend
streamlit run app.py
```

UI: **http://localhost:8501**

---

## Docker

```bash
docker-compose up --build
```

- API: `http://localhost:8000`
- Streamlit UI: `http://localhost:8501`

---

## Project Structure

```
meeting-memory-engine/
├── backend/
│   ├── pipeline/
│   │   ├── ingest.py        # Multi-format loader, chunker, Jina embeddings, ChromaDB
│   │   ├── retriever.py     # Hybrid search, temporal RAG, summaries, chat memory
│   │   ├── evaluator.py     # LLM-as-judge — faithfulness, relevance, precision
│   │   └── transcriber.py   # Audio transcription via Groq Whisper
│   ├── main.py              # FastAPI — 9 endpoints, auth, rate limiting, auto-ingest
│   └── models.py            # Pydantic schemas for all request/response payloads
├── frontend/
│   ├── app.py               # Streamlit UI — backup, deployed on Streamlit Cloud
│   └── requirements.txt     # Frontend-only dependencies
├── frontend-react/          # Primary React UI — deployed on Vercel
│   └── src/
│       ├── components/
│       │   ├── Sidebar.jsx  # Meeting list, summaries, audio upload, re-index
│       │   ├── SearchView.jsx # Search mode — question, answer, sources, action items
│       │   ├── ChatView.jsx   # Chat mode — multi-turn conversation, source tags
│       │   └── Skeleton.jsx   # Loading skeleton components
│       └── lib/
│           └── api.js       # API client for all 9 FastAPI endpoints
├── data/                    # Drop .txt / .pdf / .docx transcripts here
├── Dockerfile               # Container definition
├── docker-compose.yml       # Multi-service local orchestration
├── render.yaml              # Render deployment configuration
├── .env                     # API keys — never committed to Git
├── .gitignore
└── requirements.txt         # Backend dependencies
```

---

## Known Limitations

- **ChromaDB at scale** — suitable for ~10k chunks. At 100k+ migrate to Pinecone or Qdrant.
- **No persistent disk on Render free tier** — restarts wipe ChromaDB. Mitigated by auto-ingest on startup.
- **Free tier cold starts** — UptimeRobot minimises sleep but restarts happen occasionally. Auto-ingest runs on startup (~30 seconds).
- **Shared API key** — single key for all users. Multi-tenant auth would need user management (out of scope).
- **Hallucination risk** — mitigated by citation requirement in prompt and low temperature.
- **Re-ingest on transcribe** — `/transcribe` re-ingests all transcripts. Fine at current scale; incremental indexing needed at higher volume.

---

## Author

Built by [Jitender Singh](https://github.com/Jitender135)

**Stack:** LangChain · ChromaDB · Jina AI · Groq (LLM + Whisper) · FastAPI · React · Tailwind v4 · Streamlit · Docker · Render · Vercel · Streamlit Cloud