"""
Integration tests — RAG conversation history endpoints.

Covers:
- GET  /rag/conversations  — list stored Q&A history
- DELETE /rag/conversations/{conv_id}  — delete a conversation

Note: POST /rag/ask stores conversations as a side-effect, but testing the
full RAG pipeline (embedding + LLM) requires a live vector store. These tests
exercise the conversation storage layer directly via the repository.
"""

import pytest

from src.core import repository


# ── Helpers ───────────────────────────────────────────────────────────────────


def _store_conversation(user_id: str, question: str, answer: str, sources=None):
    """Directly store a conversation via repository (bypasses RAG pipeline)."""
    return repository.create_conversation(
        user_id=user_id,
        question=question,
        answer=answer,
        sources=sources or [],
    )


# ── GET /rag/conversations ─────────────────────────────────────────────────────


def test_list_conversations_empty(client):
    resp = client.get("/rag/conversations", headers={"X-User-Id": "dev-user"})
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_list_conversations_returns_stored_items(client):
    _store_conversation("dev-user", "What was I happy about?", "You felt happy about your project launch.")
    _store_conversation("dev-user", "Any recurring themes?", "Growth and reflection appear often.")

    resp = client.get("/rag/conversations", headers={"X-User-Id": "dev-user"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    questions = {i["question"] for i in items}
    assert "What was I happy about?" in questions
    assert "Any recurring themes?" in questions


def test_list_conversations_user_isolation(client):
    """User B cannot see User A's conversations."""
    _store_conversation("user-a", "User A question", "User A answer")

    resp = client.get("/rag/conversations", headers={"X-User-Id": "user-b"})
    assert resp.json()["items"] == []


def test_list_conversations_includes_required_fields(client):
    _store_conversation("dev-user", "How do I feel?", "You feel great!", sources=[{"entryId": "abc", "title": "Today", "snippet": "...", "score": "0.9", "createdAt": "2026-01-01"}])

    resp = client.get("/rag/conversations", headers={"X-User-Id": "dev-user"})
    item = resp.json()["items"][0]
    assert "convId" in item
    assert item["question"] == "How do I feel?"
    assert item["answer"] == "You feel great!"
    assert isinstance(item["sources"], list)
    assert "createdAt" in item


# ── DELETE /rag/conversations/{conv_id} ───────────────────────────────────────


def test_delete_conversation_removes_item(client):
    conv = _store_conversation("dev-user", "Delete me?", "Sure.")
    conv_id = conv["convId"]

    del_resp = client.delete(f"/rag/conversations/{conv_id}", headers={"X-User-Id": "dev-user"})
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    # Should no longer appear in list
    list_resp = client.get("/rag/conversations", headers={"X-User-Id": "dev-user"})
    assert list_resp.json()["items"] == []


def test_delete_conversation_404_for_nonexistent(client):
    resp = client.delete(
        "/rag/conversations/00000000-0000-0000-0000-000000000000",
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


def test_delete_conversation_user_isolation(client):
    """User B cannot delete User A's conversation."""
    conv = _store_conversation("user-a", "Private question", "Private answer")
    conv_id = conv["convId"]

    resp = client.delete(f"/rag/conversations/{conv_id}", headers={"X-User-Id": "user-b"})
    assert resp.status_code == 404

    # Still exists for user-a
    list_resp = client.get("/rag/conversations", headers={"X-User-Id": "user-a"})
    assert len(list_resp.json()["items"]) == 1


def test_list_conversations_newest_first(client):
    """Conversations are returned in descending SK order (newest first).
    Use distinct timestamps to guarantee ordering."""
    import time
    _store_conversation("dev-user", "First question", "First answer")
    time.sleep(1.1)  # Ensure different second-precision timestamps
    _store_conversation("dev-user", "Second question", "Second answer")

    resp = client.get("/rag/conversations", headers={"X-User-Id": "dev-user"})
    items = resp.json()["items"]
    assert len(items) == 2
    # Newest (second) should appear first
    assert items[0]["question"] == "Second question"
    assert items[1]["question"] == "First question"
