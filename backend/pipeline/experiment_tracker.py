"""
experiment_tracker.py — MLflow experiment tracking for the RAG pipeline.

What this tracks:
    Every RAG query is logged as an MLflow run with:
    - Parameters: question, chunk_size, top_k, retrieval_strategy, date_filter
    - Metrics: faithfulness, answer_relevancy, context_precision, num_sources
    - Artifacts: full answer text, sources list

Why MLflow over just logging to a file:
    MLflow gives you a visual dashboard to compare runs, plot metrics
    over time, and prove your current configuration is optimal.
    "I tracked 8 configurations and this one won" is a much stronger
    interview story than "I tuned it until it felt right."

Run the dashboard locally:
    mlflow ui --port 5001
    Then open http://localhost:5001
"""

import os
import json
import mlflow
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Store MLflow data in project root
MLFLOW_DB        = Path(__file__).resolve().parents[2] / "mlflow.db"
MLFLOW_URI       = f"sqlite:///{MLFLOW_DB}"
EXPERIMENT_NAME  = "meeting-memory-engine-rag"

# RAG config — these are the parameters we're tracking
RAG_CONFIG = {
    "chunk_size":          500,
    "chunk_overlap":       50,
    "top_k":               3,
    "retrieval_strategy":  "hybrid_bm25_semantic_rrf",
    "embedding_model":     "jina-embeddings-v2-base-en",
    "llm_model":           "llama-3.1-8b-instant",
    "llm_temperature":     0.2,
}


def get_or_create_experiment() -> str:
    """Get existing experiment ID or create a new one."""
    mlflow.set_tracking_uri(MLFLOW_URI)
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        experiment_id = mlflow.create_experiment(EXPERIMENT_NAME)
    else:
        experiment_id = experiment.experiment_id
    return experiment_id


def log_rag_query(
    question:          str,
    answer:            str,
    sources:           list,
    eval_scores:       dict = None,
    date_from:         str  = None,
    date_to:           str  = None,
    top_k:             int  = 3,
) -> str:
    """
    Log a single RAG query as an MLflow run.

    Args:
        question    — the user's question
        answer      — the LLM's answer
        sources     — list of source dicts from retriever
        eval_scores — dict with faithfulness, answer_relevancy, context_precision
        date_from   — optional temporal filter start
        date_to     — optional temporal filter end
        top_k       — number of chunks retrieved

    Returns:
        run_id — the MLflow run ID for reference
    """
    try:
        experiment_id = get_or_create_experiment()
        mlflow.set_tracking_uri(MLFLOW_URI)

        with mlflow.start_run(experiment_id=experiment_id) as run:

            # ── Parameters (config choices) ───────────────────────
            mlflow.log_params({
                **RAG_CONFIG,
                "top_k_used":      top_k,
                "date_filter":     bool(date_from or date_to),
                "date_from":       date_from or "none",
                "date_to":         date_to   or "none",
                "question_length": len(question),
            })

            # ── Metrics (quality scores) ──────────────────────────
            mlflow.log_metrics({
                "num_sources":     len(sources),
                "answer_length":   len(answer),
                "top_source_score": sources[0]["score"] if sources else 0.0,
            })

            if eval_scores:
                mlflow.log_metrics({
                    "faithfulness":      eval_scores.get("faithfulness",      0.0),
                    "answer_relevancy":  eval_scores.get("answer_relevancy",  0.0),
                    "context_precision": eval_scores.get("context_precision", 0.0),
                    "avg_eval_score": (
                        eval_scores.get("faithfulness",      0.0) +
                        eval_scores.get("answer_relevancy",  0.0) +
                        eval_scores.get("context_precision", 0.0)
                    ) / 3,
                })

            # ── Tags ──────────────────────────────────────────────
            mlflow.set_tags({
                "question":        question[:200],
                "has_date_filter": str(bool(date_from or date_to)),
                "source_titles":   ", ".join(s.get("title", "") for s in sources[:3]),
            })

            # ── Artifacts (full text) ─────────────────────────────
            artifact = {
                "question": question,
                "answer":   answer,
                "sources":  sources,
                "eval_scores": eval_scores or {},
            }
            artifact_path = Path(__file__).resolve().parent / "tmp_artifact.json"
            artifact_path.write_text(json.dumps(artifact, indent=2))
            mlflow.log_artifact(str(artifact_path), artifact_path="query_results")
            artifact_path.unlink(missing_ok=True)

            return run.info.run_id

    except Exception as e:
        # Never let MLflow tracking break the main pipeline
        print(f"MLflow tracking error (non-fatal): {e}")
        return ""


# ── Test directly ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing MLflow tracking...")

    run_id = log_rag_query(
        question="What did we decide about the mobile app launch?",
        answer="We decided to launch on iOS first on April 5th.",
        sources=[
            {"title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.0323},
            {"title": "Q1 Product Planning",      "date": "2024-01-15", "score": 0.0315},
        ],
        eval_scores={
            "faithfulness":      0.92,
            "answer_relevancy":  0.88,
            "context_precision": 0.85,
        },
        top_k=3,
    )

    print(f"Logged run: {run_id}")
    print(f"MLflow data stored at: {MLFLOW_DB}")
    print("Run: mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5001")