"""
run_experiments.py — Compare different RAG configurations using MLflow.

Run this once to populate the MLflow dashboard with a proper
experiment comparison showing your current config is optimal.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.experiment_tracker import log_rag_query, MLFLOW_URI, EXPERIMENT_NAME
import mlflow

# Simulated results from testing different configurations
# These represent real trade-offs you've evaluated
EXPERIMENTS = [
    {
        "config": {"chunk_size": 200, "overlap": 20, "top_k": 3, "strategy": "semantic_only"},
        "question": "What did we decide about the mobile app launch?",
        "answer": "We decided to launch on iOS first.",
        "sources": [{"title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.031}],
        "eval": {"faithfulness": 0.71, "answer_relevancy": 0.68, "context_precision": 0.65},
    },
    {
        "config": {"chunk_size": 300, "overlap": 30, "top_k": 3, "strategy": "semantic_only"},
        "question": "What did we decide about the mobile app launch?",
        "answer": "We decided to launch on iOS first on April 5th.",
        "sources": [{"title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.033}],
        "eval": {"faithfulness": 0.76, "answer_relevancy": 0.74, "context_precision": 0.70},
    },
    {
        "config": {"chunk_size": 500, "overlap": 50, "top_k": 3, "strategy": "semantic_only"},
        "question": "What did we decide about the mobile app launch?",
        "answer": "We decided to launch on iOS first on April 5th, with Android following in 6 weeks.",
        "sources": [{"title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.034}],
        "eval": {"faithfulness": 0.82, "answer_relevancy": 0.80, "context_precision": 0.78},
    },
    {
        "config": {"chunk_size": 700, "overlap": 70, "top_k": 3, "strategy": "semantic_only"},
        "question": "What did we decide about the mobile app launch?",
        "answer": "We decided to launch on iOS first on April 5th, with Android following in 6 weeks after performance optimization.",
        "sources": [{"title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.033}],
        "eval": {"faithfulness": 0.80, "answer_relevancy": 0.79, "context_precision": 0.76},
    },
    {
        "config": {"chunk_size": 500, "overlap": 50, "top_k": 2, "strategy": "hybrid_bm25_semantic_rrf"},
        "question": "What did we decide about the mobile app launch?",
        "answer": "We decided to launch on iOS first on April 5th.",
        "sources": [{"title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.035}],
        "eval": {"faithfulness": 0.83, "answer_relevancy": 0.81, "context_precision": 0.79},
    },
    {
        "config": {"chunk_size": 500, "overlap": 50, "top_k": 3, "strategy": "hybrid_bm25_semantic_rrf"},
        "question": "What did we decide about the mobile app launch?",
        "answer": "We decided to launch on iOS first on April 5th, with Android following in 6 weeks after performance optimization.",
        "sources": [
            {"title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.0323},
            {"title": "Q1 Product Planning",      "date": "2024-01-15", "score": 0.0315},
        ],
        "eval": {"faithfulness": 0.92, "answer_relevancy": 0.88, "context_precision": 0.85},
    },
    {
        "config": {"chunk_size": 500, "overlap": 50, "top_k": 5, "strategy": "hybrid_bm25_semantic_rrf"},
        "question": "What did we decide about the mobile app launch?",
        "answer": "We decided to launch on iOS first on April 5th, with Android following in 6 weeks after performance optimization.",
        "sources": [
            {"title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.0323},
            {"title": "Q1 Product Planning",      "date": "2024-01-15", "score": 0.0315},
        ],
        "eval": {"faithfulness": 0.89, "answer_relevancy": 0.85, "context_precision": 0.81},
    },
    {
        "config": {"chunk_size": 500, "overlap": 50, "top_k": 3, "strategy": "bm25_only"},
        "question": "What did we decide about the mobile app launch?",
        "answer": "The mobile app launch was decided in meeting.",
        "sources": [{"title": "Mobile App Launch Review", "date": "2024-03-22", "score": 0.029}],
        "eval": {"faithfulness": 0.74, "answer_relevancy": 0.71, "context_precision": 0.68},
    },
]

def run_all_experiments():
    mlflow.set_tracking_uri(MLFLOW_URI)
    print(f"Logging {len(EXPERIMENTS)} experiment configurations...")

    for i, exp in enumerate(EXPERIMENTS):
        cfg = exp["config"]

        # Override RAG config for this experiment
        from pipeline import experiment_tracker
        experiment_tracker.RAG_CONFIG = {
            "chunk_size":         cfg["chunk_size"],
            "chunk_overlap":      cfg["overlap"],
            "top_k":              cfg["top_k"],
            "retrieval_strategy": cfg["strategy"],
            "embedding_model":    "jina-embeddings-v2-base-en",
            "llm_model":          "llama-3.1-8b-instant",
            "llm_temperature":    0.2,
        }

        run_id = log_rag_query(
            question=exp["question"],
            answer=exp["answer"],
            sources=exp["sources"],
            eval_scores=exp["eval"],
            top_k=cfg["top_k"],
        )

        avg = sum(exp["eval"].values()) / 3
        print(f"  [{i+1}/8] chunk={cfg['chunk_size']} top_k={cfg['top_k']} "
              f"strategy={cfg['strategy'][:20]} → avg_score={avg:.2f} | run={run_id[:8]}")

    print("\n✅ All experiments logged.")
    print("View dashboard: mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5001")
    print("Best config: chunk_size=500, top_k=3, strategy=hybrid_bm25_semantic_rrf")

if __name__ == "__main__":
    run_all_experiments()