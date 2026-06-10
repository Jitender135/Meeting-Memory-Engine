Meeting Memory Engine
A Temporal RAG (Retrieval-Augmented Generation) pipeline that lets you query your past meeting transcripts using natural language.

"What did we decide about the mobile app launch?"
"What action items were assigned to Rahul in Q1?"
"Summarise all decisions made before the product pivot."

🏗️ Architecture
Transcripts (.txt) → Document Loader + Metadata Tagger → Text Chunker (chunk=500, overlap=50) → Embeddings (HuggingFace all-MiniLM-L6-v2) → ChromaDB (vector store) → Temporal Retriever (pre-retrieval date filter + cosine similarity) → Groq Llama 3.1 → FastAPI REST Endpoints → Streamlit UI
🔧 Tech Stack
LayerTechnologyRAG FrameworkLangChainVector DatabaseChromaDBEmbeddingsHuggingFace all-MiniLM-L6-v2 (local)LLMGroq — Llama 3.1 8b InstantAPI LayerFastAPI + PydanticFrontendStreamlit
🚀 Getting Started
1. Clone the repo
git clone https://github.com/Jitender135/Meeting-Memory-Engine.git
2. Create virtual environment
python -m venv venv && venv\Scripts\activate
3. Install dependencies
python -m pip install -r requirements.txt
python -m pip install langchain-groq langchain-huggingface sentence-transformers
4. Set up environment variables
Create a .env file in the root: GROQ_API_KEY=your_groq_api_key_here
Get a free key at console.groq.com
5. Add meeting transcripts
Drop .txt files into data/. Filename format: meeting_YYYY_MM_DD.txt
6. Ingest transcripts
cd backend && python pipeline/ingest.py
7. Start the API
uvicorn main:app --reload --port 8000
API docs at: http://localhost:8000/docs
8. Start the UI
cd ../frontend && streamlit run app.py
📡 API Endpoints
MethodEndpointDescriptionGET/healthLiveness check + pipeline statusGET/meetingsList all indexed meetingsPOST/ingestIngest transcripts into ChromaDBPOST/queryAsk a question, get a cited answer
💡 Key Design Decisions
Why chunk_size=500? Captures one complete meeting topic without bleeding into the next. Too small splits decisions across chunks; too large dilutes similarity scores.
Why ChromaDB over FAISS? ChromaDB stores vectors + metadata together, enabling pre-retrieval date filtering. FAISS is vectors-only — you'd build the filter layer yourself.
Why temporal pre-retrieval filtering? The LLM only sees what the retriever hands it. Filtering by date before similarity search guarantees time-accurate answers.
Why FastAPI over direct Streamlit calls? The pipeline becomes a proper service any consumer can call. Clean separation — backend owns AI logic, frontend just makes HTTP calls.
🗂️ Project Structure
meeting-memory-engine/
├── backend/
│   ├── pipeline/
│   │   ├── ingest.py
│   │   └── retriever.py
│   ├── main.py
│   └── models.py
├── frontend/
│   └── app.py
├── data/
├── .env
└── requirements.txt
👨‍💻 Author
Built by Jitender Singh as a portfolio project demonstrating production-ready RAG pipeline engineering.