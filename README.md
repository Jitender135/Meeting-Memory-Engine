# 🧠 Meeting Memory Engine

> A **Temporal RAG (Retrieval-Augmented Generation)** pipeline that lets you query your past meeting transcripts using natural language — with cited, time-accurate answers.

**Live App:** https://meeting-memory-engine-n5iyrh3cmnjkvd5scvnnpn.streamlit.app
**Live API:** https://meeting-memory-engine.onrender.com/docs

---

## 💡 The Problem

After months of meetings, nobody remembers what was decided, who committed to what, or when that pricing call happened. You dig through Slack, scan notes, and still come up empty.

**Meeting Memory Engine fixes that.**

Upload your meeting transcripts and ask:
- *"What did we decide about the mobile app launch?"*
- *"What action items were assigned to Rahul in Q1?"*
- *"Summarise all decisions made before the product pivot."*

Get cited, accurate answers with the meeting date and source — instantly.

---

## 🏗️ Architecture

```
Transcripts (.txt)
        │
        ▼
┌─────────────────────────────┐
│   Document Loader           │  TextLoader — reads .txt transcripts
│   + Metadata Tagger         │  Attaches meeting_date, title, participants
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Text Chunker              │  RecursiveCharacterTextSplitter
│   chunk=500 / overlap=50    │  Preserves semantic boundaries
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Embeddings                │  HuggingFace all-MiniLM-L6-v2
│   (local — no API key)      │  Runs entirely on CPU
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   ChromaDB                  │  Stores vectors + text + metadata
│   (persisted to disk)       │  Enables temporal date filtering
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Temporal Retriever        │  Pre-retrieval date filter ($gte/$lte)
│   (core differentiator)     │  + cosine similarity search (top-k)
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Groq — Llama 3.1 8b       │  Generates cited, grounded answers
│   (fast free inference)     │  Low temperature for factual output
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   FastAPI REST API          │  /query /ingest /meetings /health
│   + Streamlit UI            │  Clean frontend calling the API
└─────────────────────────────┘
```

---

## 🔧 Tech Stack

| Layer            | Technology                              | Why                                              |
|------------------|-----------------------------------------|--------------------------------------------------|
| RAG Framework    | LangChain                               | Best-in-class RAG orchestration                  |
| Vector Database  | ChromaDB                                | Stores vectors + metadata — enables date filters |
| Embeddings       | HuggingFace `all-MiniLM-L6-v2`         | Free, local, no API key needed                   |
| LLM              | Groq — Llama 3.1 8b Instant            | Fast, free inference with large context window   |
| API Layer        | FastAPI + Pydantic                      | Production-ready REST endpoints, auto docs       |
| Frontend         | Streamlit                               | Clean demo UI, calls FastAPI via HTTP            |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Jitender135/Meeting-Memory-Engine.git
cd Meeting-Memory-Engine
```

### 2. Create and activate virtual environment

```bash
# Create
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
python -m pip install langchain-groq langchain-huggingface sentence-transformers
```

### 4. Set up environment variables

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

> Get a free Groq API key at [console.groq.com](https://console.groq.com) — no credit card needed.

### 5. Add your meeting transcripts

Drop `.txt` transcript files into the `data/` folder.

**Required filename format:** `meeting_YYYY_MM_DD.txt`

Example:
```
data/
├── meeting_2024_01_15.txt
├── meeting_2024_03_22.txt
└── meeting_2024_06_10.txt
```

### 6. Ingest transcripts into ChromaDB

```bash
cd backend
python pipeline/ingest.py
```

Expected output:
```
Found 3 transcript(s). Starting ingest...
  Loaded: meeting_2024_01_15.txt
  Loaded: meeting_2024_03_22.txt
  Loaded: meeting_2024_06_10.txt
  Total chunks created: 6
  Ingested 6 chunks into ChromaDB.
```

### 7. Start the FastAPI backend

```bash
uvicorn main:app --reload --port 8000
```

Interactive API docs available at: **http://localhost:8000/docs**

### 8. Start the Streamlit frontend

Open a new terminal, activate venv, then:

```bash
cd frontend
streamlit run app.py
```

---

## 📡 API Endpoints

| Method | Endpoint    | Description                              |
|--------|-------------|------------------------------------------|
| GET    | `/health`   | Liveness check + pipeline status         |
| GET    | `/meetings` | List all indexed meetings with metadata  |
| POST   | `/ingest`   | Ingest all transcripts into ChromaDB     |
| POST   | `/query`    | Ask a question, get a cited answer       |

### Example — POST /query

**Request:**
```json
{
  "question": "What did we decide about the mobile app launch?",
  "date_from": "2024-01-01",
  "date_to": "2024-06-30",
  "top_k": 3
}
```

**Response:**
```json
{
  "answer": "The team decided to launch on iOS first on April 5th, with Android following in 6 weeks after performance optimization. (Mobile App Launch Review | 2024-03-22)",
  "sources": [
    { "title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.692 },
    { "title": "Q1 Product Planning",      "date": "2024-01-15", "score": 0.553 }
  ]
}
```

---

## 💡 Key Design Decisions

### Why `chunk_size=500` with `overlap=50`?
500 tokens (~375 words) captures one complete meeting topic — an agenda item, a decision, or an action block — without bleeding into the next. The 50-token overlap prevents decisions from being split at chunk edges.

### Why ChromaDB over FAISS?
ChromaDB stores vectors **and** metadata together in one place. This enables pre-retrieval date filtering — critical for temporal queries like "decisions from Q1". FAISS is vectors-only; you'd have to build the filter layer yourself.

### Why temporal pre-retrieval filtering?
The LLM only sees what the retriever hands it. Without date filtering, "what did we decide last quarter?" could return semantically similar chunks from 2 years ago. Filtering **before** similarity search guarantees time-accurate context.

### Why FastAPI over calling the pipeline directly from Streamlit?
A pipeline inside Streamlit is a demo. A pipeline behind a REST endpoint is a **service** — any consumer (Slack bot, mobile app, cron job) can call `/query` without touching AI code. Clean separation of concerns.

---

## 🗂️ Project Structure

```
meeting-memory-engine/
├── backend/
│   ├── pipeline/
│   │   ├── ingest.py        # Document loading, chunking, embedding, ChromaDB storage
│   │   └── retriever.py     # Temporal RAG chain — filter, retrieve, generate
│   ├── main.py              # FastAPI app — all 4 endpoints
│   └── models.py            # Pydantic request/response schemas
├── frontend/
│   └── app.py               # Streamlit UI — calls FastAPI via HTTP
├── data/                    # Drop your .txt meeting transcripts here
├── .env                     # API keys — never committed to Git
├── .gitignore
└── requirements.txt
```

---

## 🔮 Planned Improvements

- [ ] Action item auto-extraction from retrieved chunks
- [ ] Cross-encoder re-ranking for improved retrieval precision
- [ ] RAGAS evaluation for faithfulness and answer relevance scores
- [ ] Slack bot integration via the `/query` endpoint
- [ ] Multi-format support (PDF, DOCX transcripts)

---

## 👨‍💻 Author

Built by [Jitender Singh](https://github.com/Jitender135) as a portfolio project demonstrating production-ready RAG pipeline engineering with LangChain, ChromaDB, FastAPI, and Groq.