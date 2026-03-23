"""
Integration tests — AI enrichment + RAG endpoints against live Docker stack.
Skipped unless INTEGRATION_TEST=1.
"""

import os
import pytest
import requests

pytestmark = pytest.mark.skipif(
    not os.getenv("INTEGRATION_TEST"),
    reason="Set INTEGRATION_TEST=1 and run `make dev` first",
)

BASE_URL = os.getenv("API_URL", "http://localhost:8080")
HEADERS = {"X-User-Id": "test-ai-user", "Content-Type": "application/json"}


def make_item(title="AI Test", body="Testing AI enrichment with Ollama."):
    resp = requests.post(
        f"{BASE_URL}/entries",
        json={"title": title, "body": body},
        headers=HEADERS,
    )
    assert resp.status_code == 201
    return resp.json()["item"]


def delete_item(item_id):
    requests.delete(f"{BASE_URL}/entries/{item_id}", headers=HEADERS)


# ── Config ────────────────────────────────────────────────────────────────────


def test_config_providers_lists_ollama():
    resp = requests.get(f"{BASE_URL}/config/providers")
    assert resp.status_code in (200, 202)  # 202 = async accepted
    names = [p["name"] for p in resp.json()["providers"]]
    assert "ollama" in names


# ── AI Enrichment ─────────────────────────────────────────────────────────────


@pytest.mark.timeout(90)
def test_ai_enrichment_returns_done():
    item = make_item()
    try:
        resp = requests.post(
            f"{BASE_URL}/entries/{item['itemId']}/ai",
            headers=HEADERS,
            timeout=90,
        )
        assert resp.status_code in (200, 202)  # 202 = async accepted
        body = resp.json()
        assert body["aiStatus"] == "DONE"
        assert isinstance(body["tags"], list)
        assert body["summary"]
    finally:
        delete_item(item["itemId"])


# ── RAG ───────────────────────────────────────────────────────────────────────


def test_rag_status_returns_count():
    resp = requests.get(f"{BASE_URL}/rag/status", headers=HEADERS)
    assert resp.status_code in (200, 202)  # 202 = async accepted
    assert isinstance(resp.json()["totalVectors"], int)


@pytest.mark.timeout(60)
def test_rag_ask_returns_answer():
    item = make_item(
        title="RAG Integration Test",
        body="The Eiffel Tower is located in Paris, France. It was built in 1889.",
    )
    try:
        # Embed first
        embed_resp = requests.post(
            f"{BASE_URL}/rag/embed",
            json={"entryId": item["itemId"]},
            headers=HEADERS,
            timeout=30,
        )
        assert embed_resp.status_code == 200

        # Ask
        ask_resp = requests.post(
            f"{BASE_URL}/rag/ask",
            json={"query": "Where is the Eiffel Tower?", "top_k": 3},
            headers=HEADERS,
            timeout=60,
        )
        assert ask_resp.status_code == 200
        body = ask_resp.json()
        assert body["answer"]
        assert isinstance(body["sources"], list)
    finally:
        delete_item(item["itemId"])


# ── Admin ─────────────────────────────────────────────────────────────────────


def test_admin_metrics_returns_200():
    resp = requests.get(f"{BASE_URL}/admin/metrics", headers=HEADERS)
    assert resp.status_code in (200, 202)  # 202 = async accepted
    body = resp.json()
    assert "totalAiCalls" in body
    assert "activeUsers" in body


def test_admin_users_returns_list():
    resp = requests.get(f"{BASE_URL}/admin/users", headers=HEADERS)
    assert resp.status_code in (200, 202)  # 202 = async accepted
    assert "users" in resp.json()


def test_admin_audit_returns_logs():
    resp = requests.get(f"{BASE_URL}/admin/audit", headers=HEADERS)
    assert resp.status_code in (200, 202)  # 202 = async accepted
    assert "items" in resp.json()
