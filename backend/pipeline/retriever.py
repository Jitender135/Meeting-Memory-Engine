import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
import chromadb

# ── Load environment ──────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ── Constants ─────────────────────────────────────────────────────
CHROMA_PATH = Path(__file__).resolve().parents[2] / "chroma_db"
TOP_K = 3  # Number of chunks to retrieve — 3 is enough for meeting transcripts


# ── Prompt Template ───────────────────────────────────────────────
# Why explicit citation instruction:
# Forces LLM to ground answers in retrieved chunks, reduces hallucination
PROMPT_TEMPLATE = """
You are an intelligent meeting assistant. 
Answer the question using ONLY the meeting transcript context provided below.
Always cite which meeting (title and date) your answer comes from.
If the answer is not in the context, say "I couldn't find this in the provided meeting transcripts."

Context from meetings:
{context}

Question: {question}

Answer (with meeting citations):
"""


def get_embedding_function():
    """Same embedding model used during ingest — must match."""
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )


def get_llm():
    """
    Groq with Llama3 for fast, free inference.
    Why llama3-8b-8192: good reasoning, 8192 context window fits
    multiple retrieved chunks comfortably.
    """
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,  # Low temp = more factual, less creative
    )


def build_context(chunks: list) -> str:
    """
    Format retrieved chunks into a clean context string for the LLM.
    Each chunk is labeled with its meeting title and date.
    """
    context_parts = []
    for i, chunk in enumerate(chunks):
        meta  = chunk["metadata"]
        title = meta.get("title", "Unknown Meeting")
        date  = meta.get("meeting_date", "Unknown Date")
        text  = chunk["document"]
        context_parts.append(
            f"[Meeting {i+1}: {title} | Date: {date}]\n{text}"
        )
    return "\n\n".join(context_parts)


def query(
    question: str,
    date_from: str = None,  # format: "YYYY-MM-DD"
    date_to:   str = None,  # format: "YYYY-MM-DD"
    top_k:     int = TOP_K,
) -> dict:
    """
    Main retrieval function:
    1. Embed the question
    2. Filter ChromaDB by date range (temporal RAG)
    3. Retrieve top_k most similar chunks
    4. Build context and ask LLM
    5. Return answer + sources

    Why pre-retrieval filtering:
    Filtering BEFORE similarity search ensures the LLM only sees
    context from the correct time window — not semantically similar
    but temporally irrelevant chunks from other periods.
    """

    # ── Step 1: Embed the question ────────────────────────────────
    embed_fn  = get_embedding_function()
    query_vec = embed_fn.embed_query(question)

    # ── Step 2: Build date filter for ChromaDB ────────────────────
    where_filter = None
    if date_from or date_to:
        from datetime import datetime
        conditions = []
        if date_from:
            ts_from = int(datetime.strptime(date_from, "%Y-%m-%d").timestamp())
            conditions.append({"meeting_timestamp": {"$gte": ts_from}})
        if date_to:
            ts_to = int(datetime.strptime(date_to, "%Y-%m-%d").timestamp())
            conditions.append({"meeting_timestamp": {"$lte": ts_to}})

        where_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    # ── Step 3: Query ChromaDB ────────────────────────────────────
    client     = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection("meeting_transcripts")

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    # ── Step 4: Format retrieved chunks ──────────────────────────
    chunks = [
        {
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score":    round(1 - results["distances"][0][i], 3),
        }
        for i in range(len(results["documents"][0]))
    ]

    if not chunks:
        return {
            "answer":  "No relevant meeting transcripts found for your query.",
            "sources": [],
        }

    # ── Step 5: Build prompt and call LLM ────────────────────────
    context = build_context(chunks)
    prompt  = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )
    llm   = get_llm()
    chain = prompt | llm

    response = chain.invoke({"context": context, "question": question})

    # ── Step 6: Return structured result ─────────────────────────
    return {
        "answer": response.content.strip(),
        "sources": [
            {
                "title": c["metadata"].get("title", "Unknown"),
                "date":  c["metadata"].get("meeting_date", "Unknown"),
                "score": c["score"],
            }
            for c in chunks
        ],
    }


# ── Run directly for testing ──────────────────────────────────────
if __name__ == "__main__":
    print("=== Test 1: No date filter ===")
    result = query("What did we decide about the mobile app launch?")
    print("Answer:", result["answer"])
    print("Sources:", result["sources"])

    print("\n=== Test 2: With date filter (Q1 only) ===")
    result = query(
        question="What action items were assigned?",
        date_from="2024-01-01",
        date_to="2024-03-01",
    )
    print("Answer:", result["answer"])
    print("Sources:", result["sources"])

# ─────────────────────────────────────────────────────────────────
# ACTION ITEM EXTRACTOR
# ─────────────────────────────────────────────────────────────────

ACTION_ITEM_PROMPT = """
You are a precise meeting assistant that extracts action items from meeting transcripts.

STRICT RULES:
- Extract each action item EXACTLY ONCE — no duplicates
- Use the EXACT name, task, and date as written in the transcript
- Do NOT paraphrase or reword any action item
- Do NOT infer or create action items not explicitly stated

Given the meeting context below, return ONLY a JSON array — no preamble, no explanation:

[
  {{"owner": "Exact Name", "task": "Exact task as written", "due": "Exact date as written", "meeting": "Meeting title", "date": "YYYY-MM-DD"}},
  ...
]

If no action items found, return: []

Meeting context:
{context}
"""


def extract_action_items(
    question:  str,
    date_from: str = None,
    date_to:   str = None,
) -> dict:
    """
    Extract structured action items from meeting transcripts.

    Two-step process:
      1. Retrieve relevant chunks (same temporal RAG as query())
      2. Run a second focused LLM call with a structured output prompt
         that forces JSON — no free-form text

    Why a separate LLM call instead of combining with query():
      Action item extraction needs a different prompt and output format.
      Mixing summarisation + structured extraction in one prompt degrades
      quality on both tasks. Two focused calls beats one confused call.
    """
    # ── Step 1: Retrieve relevant chunks ─────────────────────────
    embed_fn  = get_embedding_function()
    query_vec = embed_fn.embed_query(question)

    where_filter = None
    if date_from or date_to:
        from datetime import datetime
        conditions = []
        if date_from:
            ts = int(datetime.strptime(date_from, "%Y-%m-%d").timestamp())
            conditions.append({"meeting_timestamp": {"$gte": ts}})
        if date_to:
            ts = int(datetime.strptime(date_to, "%Y-%m-%d").timestamp())
            conditions.append({"meeting_timestamp": {"$lte": ts}})
        where_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    client     = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection("meeting_transcripts")

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=4,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    chunks = [
        {
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score":    round(1 - results["distances"][0][i], 3),
        }
        for i in range(len(results["documents"][0]))
    ]

    if not chunks:
        return {"action_items": [], "sources": []}

    # ── Step 2: Build context and extract action items ────────────
    context = build_context(chunks)

    llm      = get_llm()
    response = llm.invoke(ACTION_ITEM_PROMPT.format(context=context))

    # ── Step 3: Parse JSON response safely ────────────────────────
    import json
    import re

    raw = response.content.strip()

    # Strip markdown code fences if LLM wraps output in ```json ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$",          "", raw)

    try:
        items = json.loads(raw)
        if not isinstance(items, list):
            items = []
    except json.JSONDecodeError:
        items = []

    # Deduplicate — LLM sometimes returns same item from overlapping chunks
    # Key: owner + first 20 chars of task (handles date format inconsistency)
    seen_items = set()
    deduped    = []
    for item in items:
        owner = item.get("owner", "").strip().lower()
        task  = item.get("task",  "").strip().lower()[:20]
        key   = (owner, task)
        if key not in seen_items:
            seen_items.add(key)
            deduped.append(item)
    items = deduped

    sources = [
        {
            "title": c["metadata"].get("title", "Unknown"),
            "date":  c["metadata"].get("meeting_date", "Unknown"),
            "score": c["score"],
        }
        for c in chunks
    ]

    return {"action_items": items, "sources": sources}


# ── Test directly ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== Action Item Extraction Test ===")
    result = extract_action_items("What action items were assigned?")
    print(f"Found {len(result['action_items'])} action items:")
    for item in result["action_items"]:
        print(f"  - [{item.get('owner')}] {item.get('task')} (due: {item.get('due')})")