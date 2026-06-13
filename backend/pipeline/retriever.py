import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_groq import ChatGroq
# HuggingFace replaced by Jina API embeddings for deployment compatibility
from langchain_core.prompts import PromptTemplate
import chromadb
from rank_bm25 import BM25Okapi

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
    """
    Jina AI embeddings — API-based, no local model download.
    Why Jina over local HuggingFace for deployment:
        Local HuggingFace models require 400-500MB RAM to load.
        Free tier servers cap at 512MB total — causes OOM crash.
        Jina API uses <10MB RAM, deployable on any free tier.
        jina-embeddings-v2-base-en outperforms all-MiniLM-L6-v2
        on retrieval benchmarks.
    """
    import os
    from langchain_community.embeddings import JinaEmbeddings
    return JinaEmbeddings(
        jina_api_key=os.getenv("JINA_API_KEY"),
        model_name="jina-embeddings-v2-base-en",
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


def hybrid_search(
    question:     str,
    where_filter: dict = None,
    top_k:        int  = TOP_K,
) -> list:
    """
    Hybrid search — combines BM25 keyword search with semantic vector search.

    Why hybrid over pure semantic:
      Semantic search excels at conceptual queries ("what did we decide")
      but misses exact keyword matches (names, dates, project codes).
      BM25 catches exact matches but misses meaning.
      Combining both with Reciprocal Rank Fusion (RRF) gets the best
      of both — used by Notion AI, Perplexity, and production RAG systems.

    Reciprocal Rank Fusion formula:
      score(d) = Σ 1 / (k + rank(d))
      k=60 is standard — dampens the impact of very high ranks
    """
    client     = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection("meeting_transcripts")

    # ── Fetch all chunks (with optional date filter) ──────────────
    fetch_params = {"include": ["documents", "metadatas"]}
    if where_filter:
        fetch_params["where"] = where_filter

    all_results = collection.get(**fetch_params)
    all_docs    = all_results["documents"]
    all_metas   = all_results["metadatas"]

    if not all_docs:
        return []

    # ── BM25 keyword search ───────────────────────────────────────
    tokenized = [doc.lower().split() for doc in all_docs]
    bm25      = BM25Okapi(tokenized)
    bm25_scores = bm25.get_scores(question.lower().split())
    bm25_ranked = sorted(
        range(len(bm25_scores)),
        key=lambda i: bm25_scores[i],
        reverse=True,
    )

    # ── Semantic vector search ────────────────────────────────────
    embed_fn  = get_embedding_function()
    query_vec = embed_fn.embed_query(question)

    semantic_results = collection.query(
        query_embeddings=[query_vec],
        n_results=min(top_k * 3, len(all_docs)),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )
    semantic_ids = semantic_results["documents"][0]
    semantic_ranked = [
        all_docs.index(doc)
        for doc in semantic_ids
        if doc in all_docs
    ]

    # ── Reciprocal Rank Fusion ────────────────────────────────────
    k      = 60
    scores = {}

    for rank, idx in enumerate(bm25_ranked):
        scores[idx] = scores.get(idx, 0) + 1 / (k + rank + 1)

    for rank, idx in enumerate(semantic_ranked):
        scores[idx] = scores.get(idx, 0) + 1 / (k + rank + 1)

    # ── Return top_k fused results ────────────────────────────────
    top_indices = sorted(scores, key=scores.__getitem__, reverse=True)[:top_k]

    return [
        {
            "document": all_docs[i],
            "metadata": all_metas[i],
            "score":    round(scores[i], 4),
        }
        for i in top_indices
    ]


def query(
    question:  str,
    date_from: str = None,
    date_to:   str = None,
    top_k:     int = TOP_K,
) -> dict:
    """
    Main query function — now powered by hybrid search.
    Temporal filtering applied before hybrid retrieval.
    """
    # ── Build date filter ─────────────────────────────────────────
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

    # ── Hybrid retrieval ──────────────────────────────────────────
    chunks = hybrid_search(question, where_filter, top_k)

    if not chunks:
        return {
            "answer":  "No relevant meeting transcripts found.",
            "sources": [],
        }

    # ── Build prompt and call LLM ─────────────────────────────────
    context = build_context(chunks)
    prompt  = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )
    llm      = get_llm()
    chain    = prompt | llm
    response = chain.invoke({"context": context, "question": question})

    return {
        "answer": response.content.strip(),
        "sources": [
            {
                "title":   c["metadata"].get("title", "Unknown"),
                "date":    c["metadata"].get("meeting_date", "Unknown"),
                "score":   c["score"],
                "excerpt": c["document"][:300],
            }
            for c in chunks
        ],
    }
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

# ─────────────────────────────────────────────────────────────────
# CONVERSATIONAL QUERY
# ─────────────────────────────────────────────────────────────────

CONVERSATIONAL_PROMPT = """
You are an intelligent meeting assistant with access to past meeting transcripts.
You are in an ongoing conversation. Use the conversation history to understand
references like "that", "it", "they", "the decision", "who was responsible" etc.

Conversation History:
{history}

Retrieved Meeting Context:
{context}

Current Question: {question}

Instructions:
- Use conversation history to resolve references in the current question
- Answer using ONLY the meeting context provided
- Always cite which meeting (title and date) your answer comes from
- If the answer is not in the context, say so clearly

Answer:
"""


def conversational_query(
    question:  str,
    history:   list[dict],
    date_from: str = None,
    date_to:   str = None,
    top_k:     int = TOP_K,
) -> dict:
    """
    Conversational RAG query with memory.

    Why we pass history into the prompt rather than using
    LangChain ConversationBufferMemory:
        ConversationBufferMemory stores state server-side which
        breaks stateless FastAPI design. Instead we pass the full
        conversation history from the client on every request —
        stateless backend, stateful frontend. This is the correct
        pattern for REST APIs.

    Args:
        question  — current user question
        history   — list of {role, content} dicts from previous turns
        date_from — optional temporal filter start
        date_to   — optional temporal filter end
        top_k     — chunks to retrieve
    """
    # ── Build date filter ─────────────────────────────────────────
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

    # ── Hybrid retrieval ──────────────────────────────────────────
    # Enrich query with last assistant answer for better retrieval
    last_answer = ""
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            last_answer = turn.get("content", "")
            break

    enriched_question = f"{question} {last_answer[:150]}" if last_answer else question
    chunks = hybrid_search(enriched_question, where_filter, top_k)

    if not chunks:
        return {
            "answer":  "I couldn't find relevant information in the meeting transcripts.",
            "sources": [],
        }

    # ── Format conversation history ───────────────────────────────
    history_text = ""
    for turn in history[-6:]:  # last 6 turns — avoid token overflow
        role    = "User"      if turn.get("role") == "user"      else "Assistant"
        content = turn.get("content", "")
        history_text += f"{role}: {content}\n"

    if not history_text:
        history_text = "No previous conversation."

    # ── Build prompt and call LLM ─────────────────────────────────
    context  = build_context(chunks)
    prompt   = PromptTemplate(
        template=CONVERSATIONAL_PROMPT,
        input_variables=["history", "context", "question"],
    )
    llm      = get_llm()
    chain    = prompt | llm
    response = chain.invoke({
        "history":  history_text,
        "context":  context,
        "question": question,
    })

    return {
        "answer": response.content.strip(),
        "sources": [
            {
                "title":   c["metadata"].get("title",        "Unknown"),
                "date":    c["metadata"].get("meeting_date", "Unknown"),
                "score":   c["score"],
                "excerpt": c["document"][:300],
            }
            for c in chunks
        ],
    }


# ── Test directly ─────────────────────────────────────────────────
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

    print("\n=== Test 3: Conversational memory ===")
    history = [
        {"role": "user",      "content": "What did we decide about the mobile app launch?"},
        {"role": "assistant", "content": "We decided to launch on iOS first on April 5th, with Android following in 6 weeks."},
    ]
    result = conversational_query(
        question="Who was responsible for that?",
        history=history,
    )
    print("Answer:", result["answer"])
    print("Sources:", result["sources"])

    print("\n=== Action Item Extraction Test ===")
    result = extract_action_items("What action items were assigned?")
    print(f"Found {len(result['action_items'])} action items:")
    for item in result["action_items"]:
        print(f"  - [{item.get('owner')}] {item.get('task')} (due: {item.get('due')})")

# ── Test directly ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== Action Item Extraction Test ===")
    result = extract_action_items("What action items were assigned?")
    print(f"Found {len(result['action_items'])} action items:")
    for item in result["action_items"]:
        print(f"  - [{item.get('owner')}] {item.get('task')} (due: {item.get('due')})")