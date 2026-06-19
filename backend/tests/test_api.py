"""
test_api.py — Integration tests for the Meeting Memory Engine FastAPI endpoints.

Why integration tests over unit tests here:
    The core value of this system is the pipeline working end-to-end.
    Unit testing individual functions (embed, retrieve, generate) would
    require mocking the entire LLM and vector store — producing tests
    that don't reflect real behavior. Integration tests against a running
    FastAPI app catch real failures: missing env vars, broken imports,
    schema mismatches, auth failures.

Run with:
    cd backend
    pytest tests/ -v
"""

import os
import pytest
from fastapi.testclient import TestClient

# Add backend to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app

client = TestClient(app)

API_KEY     = os.getenv("APP_API_KEY", "mme-secret-2024")
AUTH_HEADER = {"X-API-Key": API_KEY}


# ─────────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────────

class TestHealth:

    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_response_schema(self):
        r = client.get("/health")
        data = r.json()
        assert "status" in data
        assert "pipeline" in data
        assert data["status"] == "ok"

    def test_health_no_auth_required(self):
        """Health endpoint must be public — monitoring tools need it."""
        r = client.get("/health")
        assert r.status_code != 401

    def test_health_head_method(self):
        """UptimeRobot uses HEAD — must not return 405."""
        r = client.head("/health")
        assert r.status_code != 405


# ─────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────

class TestAuth:

    def test_no_api_key_returns_401(self):
        r = client.post("/query", json={"question": "test"})
        assert r.status_code == 401

    def test_wrong_api_key_returns_401(self):
        r = client.post(
            "/query",
            json={"question": "test"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert r.status_code == 401

    def test_correct_api_key_passes_auth(self):
        """Correct key should not return 401 (may return other errors)."""
        r = client.post(
            "/query",
            json={"question": "What did we decide?"},
            headers=AUTH_HEADER,
        )
        assert r.status_code != 401

    def test_meetings_requires_auth(self):
        r = client.get("/meetings")
        assert r.status_code == 401

    def test_ingest_requires_auth(self):
        r = client.post("/ingest")
        assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────
# MEETINGS
# ─────────────────────────────────────────────────────────────────

class TestMeetings:

    def test_meetings_returns_200(self):
        r = client.get("/meetings", headers=AUTH_HEADER)
        assert r.status_code == 200

    def test_meetings_response_schema(self):
        r = client.get("/meetings", headers=AUTH_HEADER)
        data = r.json()
        assert "total" in data
        assert "meetings" in data
        assert isinstance(data["meetings"], list)
        assert isinstance(data["total"], int)

    def test_meetings_items_have_required_fields(self):
        r = client.get("/meetings", headers=AUTH_HEADER)
        data = r.json()
        for meeting in data["meetings"]:
            assert "title" in meeting
            assert "date" in meeting
            assert "source_file" in meeting

    def test_meetings_sorted_by_date(self):
        r = client.get("/meetings", headers=AUTH_HEADER)
        dates = [m["date"] for m in r.json()["meetings"]]
        assert dates == sorted(dates)


# ─────────────────────────────────────────────────────────────────
# QUERY
# ─────────────────────────────────────────────────────────────────

class TestQuery:

    def test_query_returns_200(self):
        r = client.post(
            "/query",
            json={"question": "What did we decide about the mobile app launch?"},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200

    def test_query_response_schema(self):
        r = client.post(
            "/query",
            json={"question": "What did we decide about the mobile app launch?"},
            headers=AUTH_HEADER,
        )
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert len(data["answer"]) > 0

    def test_query_sources_have_required_fields(self):
        r = client.post(
            "/query",
            json={"question": "What did we decide about the mobile app launch?"},
            headers=AUTH_HEADER,
        )
        for source in r.json()["sources"]:
            assert "title" in source
            assert "date" in source
            assert "score" in source

    def test_query_with_date_filter(self):
        r = client.post(
            "/query",
            json={
                "question": "What action items were assigned?",
                "date_from": "2024-01-01",
                "date_to": "2024-03-31",
            },
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200
        for source in r.json()["sources"]:
            assert source["date"] >= "2024-01-01"
            assert source["date"] <= "2024-03-31"

    def test_query_empty_question_returns_422(self):
        r = client.post(
            "/query",
            json={"question": ""},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 422

    def test_query_missing_question_returns_422(self):
        r = client.post("/query", json={}, headers=AUTH_HEADER)
        assert r.status_code == 422

    def test_query_top_k_respected(self):
        r = client.post(
            "/query",
            json={"question": "What did we decide?", "top_k": 2},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200
        assert len(r.json()["sources"]) <= 2


# ─────────────────────────────────────────────────────────────────
# ACTION ITEMS
# ─────────────────────────────────────────────────────────────────

class TestActionItems:

    def test_action_items_returns_200(self):
        r = client.post(
            "/action-items",
            json={"question": "What action items were assigned?"},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200

    def test_action_items_response_schema(self):
        r = client.post(
            "/action-items",
            json={"question": "What action items were assigned?"},
            headers=AUTH_HEADER,
        )
        data = r.json()
        assert "action_items" in data
        assert "sources" in data
        assert isinstance(data["action_items"], list)

    def test_action_items_fields(self):
        r = client.post(
            "/action-items",
            json={"question": "What action items were assigned?"},
            headers=AUTH_HEADER,
        )
        for item in r.json()["action_items"]:
            assert "owner" in item
            assert "task" in item


# ─────────────────────────────────────────────────────────────────
# CHAT
# ─────────────────────────────────────────────────────────────────

class TestChat:

    def test_chat_returns_200(self):
        r = client.post(
            "/chat",
            json={
                "question": "What did we decide about the mobile app?",
                "history": [],
            },
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200

    def test_chat_response_schema(self):
        r = client.post(
            "/chat",
            json={
                "question": "What did we decide about the mobile app?",
                "history": [],
            },
            headers=AUTH_HEADER,
        )
        data = r.json()
        assert "answer" in data
        assert "sources" in data

    def test_chat_with_history(self):
        r = client.post(
            "/chat",
            json={
                "question": "Who was responsible for that?",
                "history": [
                    {
                        "role": "user",
                        "content": "What did we decide about the mobile app launch?"
                    },
                    {
                        "role": "assistant",
                        "content": "We decided to launch on iOS first on April 5th."
                    },
                ],
            },
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200
        assert len(r.json()["answer"]) > 0


# ─────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────

class TestSummary:

    def test_summary_returns_200(self):
        r = client.get("/summary/2024-01-15", headers=AUTH_HEADER)
        assert r.status_code == 200

    def test_summary_response_schema(self):
        r = client.get("/summary/2024-01-15", headers=AUTH_HEADER)
        data = r.json()
        assert "status" in data
        assert "title" in data
        assert "date" in data
        assert "key_decisions" in data
        assert "action_items" in data
        assert "open_questions" in data

    def test_summary_invalid_date_returns_404(self):
        r = client.get("/summary/1900-01-01", headers=AUTH_HEADER)
        assert r.status_code == 404

    def test_summary_invalid_format_returns_404(self):
        r = client.get("/summary/not-a-date", headers=AUTH_HEADER)
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────
# EVALUATE
# ─────────────────────────────────────────────────────────────────

class TestEvaluate:

    def test_evaluate_returns_200(self):
        r = client.post(
            "/evaluate",
            json={
                "question": "What did we decide about the mobile app launch?",
                "answer": "We decided to launch on iOS first on April 5th.",
                "contexts": [
                    "The team decided to launch on iOS first. Android to follow in 6 weeks."
                ],
            },
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200

    def test_evaluate_response_schema(self):
        r = client.post(
            "/evaluate",
            json={
                "question": "What did we decide?",
                "answer": "We decided to launch on iOS first.",
                "contexts": ["The team decided to launch on iOS first."],
            },
            headers=AUTH_HEADER,
        )
        data = r.json()
        assert "faithfulness" in data
        assert "answer_relevancy" in data
        assert "context_precision" in data