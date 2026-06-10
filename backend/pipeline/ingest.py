import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb

# ── Load environment ──────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ── Constants ─────────────────────────────────────────────────────
CHROMA_PATH = Path(__file__).resolve().parents[2] / "chroma_db"
DATA_PATH   = Path(__file__).resolve().parents[2] / "data"

CHUNK_SIZE    = 500   # ~375 words — fits one meeting topic cleanly
CHUNK_OVERLAP = 50    # 10% overlap — prevents decisions split at edges


def extract_metadata(filename: str) -> dict:
    """
    Pull meeting date from filename like meeting_2024_01_15.txt
    and return structured metadata dict.
    """
    stem = Path(filename).stem  # meeting_2024_01_15
    parts = stem.split("_")     # ['meeting', '2024', '01', '15']

    try:
        date_str = f"{parts[1]}-{parts[2]}-{parts[3]}"
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        timestamp = int(date_obj.timestamp())  # ChromaDB filters on integers
    except (IndexError, ValueError):
        date_str  = "unknown"
        timestamp = 0

    return {
        "meeting_date": date_str,
        "meeting_timestamp": timestamp,
        "source_file": filename,
    }


def load_and_enrich(file_path: Path) -> list:
    """
    Load a single transcript, attach metadata to every document chunk.
    """
    loader   = TextLoader(str(file_path), encoding="utf-8")
    docs     = loader.load()
    metadata = extract_metadata(file_path.name)

    # Read the first line to extract the meeting title
    first_line = docs[0].page_content.split("\n")[0] if docs else ""
    metadata["title"] = first_line.replace("Meeting Title:", "").strip()

    for doc in docs:
        doc.metadata.update(metadata)

    return docs


def chunk_documents(docs: list) -> list:
    """
    Split documents into chunks.
    Why RecursiveCharacterTextSplitter:
      - Tries to split on paragraphs first, then sentences, then words
      - Preserves semantic boundaries better than a naive character split
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
    )
    return splitter.split_documents(docs)


def get_embedding_function():
    """
    Use a free local HuggingFace model for embeddings.
    No API key needed — runs entirely on your machine.
    """
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )


def ingest_all(data_path: Path = DATA_PATH) -> dict:
    """
    Main ingest function:
    1. Load all .txt transcripts from data/
    2. Enrich with metadata
    3. Chunk
    4. Embed and store in ChromaDB
    """
    txt_files = list(data_path.glob("*.txt"))
    if not txt_files:
        return {"status": "error", "message": "No .txt files found in data/"}

    print(f"Found {len(txt_files)} transcript(s). Starting ingest...")

    # Load and enrich all files
    all_docs = []
    for f in txt_files:
        docs = load_and_enrich(f)
        all_docs.extend(docs)
        print(f"  Loaded: {f.name} ({len(docs)} doc(s))")

    # Chunk all documents
    chunks = chunk_documents(all_docs)
    print(f"  Total chunks created: {len(chunks)}")

    # Set up ChromaDB client (persists to disk automatically)
    client     = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name="meeting_transcripts",
        metadata={"hnsw:space": "cosine"},  # cosine similarity for text
    )

    # Get embedding function
    embed_fn = get_embedding_function()

    # Embed and upsert chunks into ChromaDB
    for i, chunk in enumerate(chunks):
        embedding = embed_fn.embed_query(chunk.page_content)
        collection.upsert(
            ids=[f"chunk_{i}"],
            embeddings=[embedding],
            documents=[chunk.page_content],
            metadatas=[chunk.metadata],
        )

    print(f"  Ingested {len(chunks)} chunks into ChromaDB.")
    return {
        "status":      "success",
        "files":       len(txt_files),
        "chunks":      len(chunks),
        "collection":  "meeting_transcripts",
    }


# ── Run directly for testing ──────────────────────────────────────
if __name__ == "__main__":
    result = ingest_all()
    print("\nIngest complete:", result)