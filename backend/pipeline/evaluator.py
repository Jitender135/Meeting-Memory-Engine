"""
evaluator.py — Custom RAG evaluation using LLM-as-judge pattern.

Why custom over RAGAS:
    RAGAS has deep dependency conflicts with LangChain 1.x.
    This implementation uses the same LLM-as-judge methodology
    but is lightweight, dependency-free, and fully within our stack.

Metrics:
    Faithfulness      — are all claims grounded in retrieved context? (0-1)
    Answer Relevance  — does the answer address the question? (0-1)
    Context Precision — are retrieved chunks relevant to the question? (0-1)
"""

import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# ── Environment ───────────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ── Prompts ───────────────────────────────────────────────────────

FAITHFULNESS_PROMPT = """
You are a RAG evaluation expert. Score whether the answer is grounded in the context.

Question: {question}
Context: {context}
Answer: {answer}

Instructions:
- Score 0.9-1.0 if all major claims in the answer are supported by the context
- Score 0.6-0.8 if most claims are supported but some details differ slightly
- Score 0.3-0.5 if only some claims are supported
- Score 0.0-0.2 if the answer contradicts or ignores the context entirely

Respond ONLY with valid JSON, no markdown, no explanation outside JSON:
{{"score": 0.00, "reason": "one sentence reason"}}
"""

ANSWER_RELEVANCE_PROMPT = """
You are a RAG evaluation expert. Score whether the answer addresses the question.

Question: {question}
Answer: {answer}

Instructions:
- Score 0.9-1.0 if the answer directly and completely addresses the question
- Score 0.6-0.8 if the answer mostly addresses the question with minor gaps
- Score 0.3-0.5 if the answer partially addresses the question
- Score 0.0-0.2 if the answer is completely off-topic

Respond ONLY with valid JSON, no markdown, no explanation outside JSON:
{{"score": 0.0, "reason": "one sentence reason"}}
"""

CONTEXT_PRECISION_PROMPT = """
You are a RAG evaluation expert. Score whether the retrieved context is relevant.

Question: {question}
Retrieved Context: {context}

Instructions:
- Score 0.9-1.0 if the context directly contains information needed to answer the question
- Score 0.6-0.8 if the context is mostly relevant with some noise
- Score 0.3-0.5 if the context is partially relevant
- Score 0.0-0.2 if the context is completely irrelevant to the question

Respond ONLY with valid JSON, no markdown, no explanation outside JSON:
{{"score": 0.0, "reason": "one sentence reason"}}
"""


def get_llm():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )


def parse_score(response_text: str) -> tuple[float, str]:
    """
    Safely parse score and reason from LLM JSON response.
    Handles cases where LLM wraps output in markdown code fences.
    """
    raw = response_text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$",          "", raw)

    try:
        data   = json.loads(raw)
        score  = float(data.get("score",  0.0))
        reason = str(data.get("reason", "No reason provided."))
        score  = max(0.0, min(1.0, score))  # clamp to 0-1
        return score, reason
    except Exception:
        return 0.0, "Could not parse evaluation response."


def evaluate_pipeline(
    question: str,
    answer:   str,
    contexts: list[str],
) -> dict:
    """
    Evaluate a single RAG response using LLM-as-judge pattern.

    Three independent LLM calls — one per metric — to avoid
    the model anchoring on previous scores.

    Args:
        question — original user question
        answer   — LLM generated answer
        contexts — list of raw retrieved chunk texts

    Returns scores dict with all three metrics + reasons.
    """
    llm          = get_llm()
    context_text = "\n\n".join(contexts)

    # ── Faithfulness ──────────────────────────────────────────────
    f_response  = llm.invoke(FAITHFULNESS_PROMPT.format(
        question=question,
        context=context_text,
        answer=answer,
    ))
    f_score, f_reason = parse_score(f_response.content)

    # ── Answer Relevance ──────────────────────────────────────────
    ar_response = llm.invoke(ANSWER_RELEVANCE_PROMPT.format(
        question=question,
        answer=answer,
    ))
    ar_score, ar_reason = parse_score(ar_response.content)

    # ── Context Precision ─────────────────────────────────────────
    cp_response = llm.invoke(CONTEXT_PRECISION_PROMPT.format(
        question=question,
        context=context_text,
    ))
    cp_score, cp_reason = parse_score(cp_response.content)

    # ── Overall score — weighted average ─────────────────────────
    # Faithfulness weighted highest — hallucination is the biggest risk
    overall = round(
        (f_score * 0.5) + (ar_score * 0.3) + (cp_score * 0.2), 3
    )

    return {
        "status":            "success",
        "overall":           overall,
        "faithfulness":      {"score": f_score,  "reason": f_reason},
        "answer_relevancy":  {"score": ar_score, "reason": ar_reason},
        "context_precision": {"score": cp_score, "reason": cp_reason},
    }


# ── Test directly ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent))
    from retriever import query

    question = "What did we decide about the mobile app launch?"
    result   = query(question)

    print("Running evaluation...")
    # Fetch actual chunk texts from ChromaDB for evaluation
    import chromadb
    from pathlib import Path
    CHROMA_PATH = Path(__file__).resolve().parents[2] / "chroma_db"
    client      = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection  = client.get_collection("meeting_transcripts")

    from langchain_huggingface import HuggingFaceEmbeddings
    embed_fn  = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
    query_vec = embed_fn.embed_query(question)

    raw = collection.query(query_embeddings=[query_vec], n_results=3, include=["documents"])
    contexts = raw["documents"][0]

    scores = evaluate_pipeline(
        question=question,
        answer=result["answer"],
        contexts=contexts,
    )

    print(f"\nOverall Score:      {scores['overall']}")
    print(f"Faithfulness:       {scores['faithfulness']['score']} — {scores['faithfulness']['reason']}")
    print(f"Answer Relevancy:   {scores['answer_relevancy']['score']} — {scores['answer_relevancy']['reason']}")
    print(f"Context Precision:  {scores['context_precision']['score']} — {scores['context_precision']['reason']}")