# Meeting Memory Engine

A production-ready **Temporal RAG (Retrieval-Augmented Generation)** system that lets you query past meeting transcripts using natural language — with cited, time-accurate, grounded answers.

**Live App:** https://meeting-memory-engine-n5iyrh3cmnjkvd5scvnnpn.streamlit.app
**Live API:** https://meeting-memory-engine.onrender.com/docs
**GitHub:** https://github.com/Jitender135/Meeting-Memory-Engine

> Note: Hosted on free tier. If the API is sleeping, click "Wake up server" in the sidebar and wait ~30 seconds. UptimeRobot pings the server every 5 minutes to minimise this.

---

## The Problem

After months of meetings, nobody remembers what was decided, who committed to what, or when that pricing discussion happened. You dig through Slack, scan notes, and still come up empty.

**Meeting Memory Engine fixes that.**

Upload your meeting transcripts and ask:
- *"What did we decide about the mobile app launch?"*
- *"What action items were assigned to Rahul in Q1?"*
- *"Summarise all decisions made before the product pivot."*
- *"Who was responsible for that?"* — and follow up conversationally

Get cited, accurate answers with the meeting date and source — instantly.

---

## Architecture

```
Transcripts (TXT / PDF / DOCX)
        │
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
│   FastAPI REST API              │  7 endpoints, API key auth,
│                                 │  rate limiting, structured logging
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│   Streamlit UI                  │  Search mode + Chat mode
│                                 │  Answer + Sources + Action Items
│                                 │  + Pipeline Quality scores
└─────────────────────────────────┘
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
| API Layer | FastAPI + Pydantic | REST endpoints, auto OpenAPI docs, request validation |
| Auth | API Key Header (X-API-Key) | Protects all pipeline endpoints |
| Rate Limiting | slowapi | 10 requests/minute per IP |
| Logging | loguru | Structured logs, daily rotation, 7-day retention |
| Frontend | Streamlit | Clean internal tool UI, calls FastAPI via HTTP |
| Containerisation | Docker + docker-compose | Consistent builds, deployable anywhere |
| Backend Hosting | Render | Free tier, auto-deploy on GitHub push |
| Frontend Hosting | Streamlit Community Cloud | Free, auto-deploy on push |
| Uptime Monitoring | UptimeRobot | Pings /health every 5 minutes to prevent sleep |

---

## Features

### Core Pipeline
- **Temporal RAG** — pre-retrieval date filtering using ChromaDB `where` clause. "What did we decide last quarter?" only retrieves chunks from that time window — not semantically similar but temporally wrong results. This is the core differentiator.
- **Hybrid Search** — BM25 keyword search + semantic vector search combined with Reciprocal Rank Fusion (RRF). Pure semantic search misses exact keyword matches (names, dates, project codes). BM25 catches those.
- **Multi-format Ingestion** — ingests `.txt`, `.pdf` (via PyMuPDF), and `.docx` (via python-docx) transcripts. Extracts clean text from each format and attaches structured metadata.
- **Cited Answers** — every answer includes the meeting title and date it was sourced from.

### Advanced Features
- **Action Item Extractor** — second focused LLM call extracts structured action items (owner, task, due date, meeting). Returns as a clean table in the UI. Deduplicated at the prompt level to prevent duplicate entries from overlapping chunks.
- **Conversational Memory** — multi-turn chat mode. Ask a question then follow up with "Who was responsible for that?" — the LLM resolves references using conversation history. Stateless backend pattern: history sent by client on every request, no server-side session storage.
- **Custom RAG Evaluator** — LLM-as-judge pattern measuring three metrics: Faithfulness, Answer Relevance, Context Precision. Built custom instead of RAGAS due to hard dependency conflicts (RAGAS requires LangChain 0.2.x, this project uses 1.x). Three independent LLM calls — one per metric — to avoid score anchoring.
- **Auto-ingest on Startup** — if ChromaDB collection is missing on startup (e.g. after free tier restart), the server automatically ingests all transcripts from `data/`.

### Production Hardening
- API key authentication on all pipeline endpoints (`X-API-Key` header)
- Rate limiting: 10 requests/minute per IP
- Structured logging: every request logged with timestamp, method, question preview
- CORS middleware configured
- Health check endpoint reporting pipeline status
- Docker + docker-compose for consistent deployment
- UptimeRobot monitoring every 5 minutes

---

## API Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|---|---|---|---|---|
| GET | `/health` | None | None | Liveness check + pipeline status |
| GET | `/meetings` | Required | 30/min | List all indexed meetings |
| POST | `/ingest` | Required | 5/min | Ingest transcripts into ChromaDB |
| POST | `/query` | Required | 10/min | Ask a question, get a cited answer |
| POST | `/action-items` | Required | 10/min | Extract structured action items |
| POST | `/evaluate` | Required | 10/min | Evaluate RAG response quality |
| POST | `/chat` | Required | 10/min | Multi-turn conversational query |

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

### POST /action-items — Example

**Response:**
```json
{
  "action_items": [
    { "owner": "Amit", "task": "Onboarding prototype by Feb 10", "due": "Feb 10", "meeting": "Q1 Product Planning", "date": "2024-01-15" },
    { "owner": "Sarah", "task": "Retention dashboard by Jan 22", "due": "Jan 22", "meeting": "Q1 Product Planning", "date": "2024-01-15" }
  ],
  "sources": [...]
}
```

---

## Key Design Decisions

**Why `chunk_size=500` with `overlap=50`?**
500 tokens (~375 words) captures one complete meeting topic without bleeding into the next. The 50-token overlap prevents decisions from being split at chunk edges. Trade-off: larger overlap means more redundant storage — acceptable for transcript-sized documents.

**Why ChromaDB over FAISS?**
ChromaDB stores vectors and metadata together. This enables pre-retrieval date filtering — FAISS is vectors-only, you'd build the filter layer yourself. Trade-off: ChromaDB suits ~10k chunks. At 100k+ migrate to Pinecone or Qdrant.

**Why temporal pre-retrieval filtering?**
The LLM only sees what the retriever hands it. Without date filtering, "what did we decide last quarter?" can return semantically similar chunks from two years ago. Filtering before similarity search guarantees time-accurate context. This is the key insight of the project.

**Why hybrid search?**
Pure semantic search misses exact keyword matches. If someone asks "What did Amit commit to?", semantic search may miss it because "commit" doesn't vector-match well to "Action Items: Amit:...". BM25 catches exact matches. Combining both with RRF gives higher precision than either alone.

**Why FastAPI over calling the pipeline directly from Streamlit?**
A pipeline inside Streamlit is a demo. A pipeline behind a REST endpoint is a service — any consumer (Slack bot, mobile app, cron job) can call `/query` without touching AI code. Also testable independently with curl.

**Why Jina AI embeddings instead of local HuggingFace?**
Local HuggingFace models require 400-500MB RAM. Render free tier caps at 512MB total — causes OOM crashes. Jina API-based embeddings use less than 10MB RAM and perform comparably on retrieval benchmarks for clean professional text.

**Why custom RAG evaluator instead of RAGAS?**
RAGAS requires LangChain 0.2.x which conflicts hard with our 1.x stack. The LLM-as-judge pattern gives identical methodology with zero dependency risk. Three independent LLM calls avoid score anchoring. This also shows problem-solving judgment rather than just package installation.

**Why stateless conversational memory?**
Stateful server-side memory breaks horizontal scaling and makes the API harder to test. Passing history from the client on every request keeps the backend stateless — correct REST pattern. The client owns state, the server owns logic.

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

```
data/
├── meeting_2024_01_15.txt
├── meeting_2024_03_22.pdf
└── meeting_2024_06_10.docx
```

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

### 8. Start the Streamlit frontend

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
- UI: `http://localhost:8501`

---

## Project Structure

```
meeting-memory-engine/
├── backend/
│   ├── pipeline/
│   │   ├── ingest.py       # Multi-format loader, chunker, Jina embeddings, ChromaDB
│   │   ├── retriever.py    # Hybrid search, temporal RAG, action extractor, chat memory
│   │   └── evaluator.py    # LLM-as-judge evaluation — faithfulness, relevance, precision
│   ├── main.py             # FastAPI — 7 endpoints, auth, rate limiting, logging, auto-ingest
│   └── models.py           # Pydantic schemas for all request/response payloads
├── frontend/
│   ├── app.py              # Streamlit UI — Search mode + Chat mode
│   └── requirements.txt    # Frontend-only dependencies for Streamlit Cloud
├── data/                   # Drop .txt / .pdf / .docx transcripts here
├── Dockerfile              # Container definition
├── docker-compose.yml      # Multi-service local orchestration
├── render.yaml             # Render deployment configuration
├── .env                    # API keys — never committed to Git
├── .gitignore
└── requirements.txt        # Backend dependencies
```

---

## Known Limitations

- **ChromaDB at scale** — suitable for ~10k chunks. At 100k+ migrate to Pinecone or Qdrant.
- **No persistent disk on Render free tier** — restarts wipe ChromaDB. Mitigated by auto-ingest on startup.
- **Free tier cold starts** — UptimeRobot minimises sleep but restarts still happen occasionally. First request after restart triggers auto-ingest (~30 seconds).
- **Shared API key** — single key for all users. Multi-tenant auth would need user management (out of scope).
- **Hallucination risk** — mitigated by citation requirement in prompt and low temperature, but not eliminated for ambiguous chunks.

---

## Author

Built by [Jitender Singh](https://github.com/Jitender135)

**Stack:** LangChain · ChromaDB · Jina AI · Groq · FastAPI · Streamlit · Docker · Render · Streamlit Cloud