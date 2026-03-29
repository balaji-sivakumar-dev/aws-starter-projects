"""
Integration tests — run against the live Docker stack (make dev).

Skipped automatically when INTEGRATION_TEST env var is not set.
Run with:
    make test-integration
    INTEGRATION_TEST=1 pytest services/api/tests/integration/ -v
"""

import os
import uuid

import pytest
import requests

# Skip if not running in integration mode
pytestmark = pytest.mark.skipif(
    not os.getenv("INTEGRATION_TEST"),
    reason="Set INTEGRATION_TEST=1 and run `make dev` first",
)

BASE_URL = os.getenv("API_URL", "http://localhost:8080")
HEADERS = {"X-User-Id": "test-integration-user", "Content-Type": "application/json"}


@pytest.fixture(autouse=True)
def cleanup_items():
    """Track and delete all items created during a test."""
    created = []
    yield created
    for item_id in created:
        requests.delete(f"{BASE_URL}/entries/{item_id}", headers=HEADERS)


def make_item(title="Integration Test Item", body="Body text", track=None):
    resp = requests.post(
        f"{BASE_URL}/entries",
        json={"title": title, "body": body},
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()["item"]
    if track is not None:
        track.append(item["itemId"])
    return item


# ── Health ────────────────────────────────────────────────────────────────────


def test_health():
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Items CRUD ────────────────────────────────────────────────────────────────


def test_create_item_returns_201(cleanup_items):
    item = make_item(track=cleanup_items)
    assert item["title"] == "Integration Test Item"
    assert "itemId" in item
    assert item["aiStatus"] == "NOT_REQUESTED"


def test_list_items_includes_created(cleanup_items):
    item = make_item(title="List Integration Test", track=cleanup_items)
    resp = requests.get(f"{BASE_URL}/entries", headers=HEADERS)
    assert resp.status_code == 200
    ids = [i["itemId"] for i in resp.json()["items"]]
    assert item["itemId"] in ids


def test_get_item_by_id(cleanup_items):
    item = make_item(track=cleanup_items)
    resp = requests.get(f"{BASE_URL}/entries/{item['itemId']}", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["item"]["title"] == item["title"]


def test_update_item(cleanup_items):
    item = make_item(track=cleanup_items)
    resp = requests.put(
        f"{BASE_URL}/entries/{item['itemId']}",
        json={"title": "Updated Title", "body": "Updated body"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["item"]["title"] == "Updated Title"


def test_delete_item_then_404(cleanup_items):
    item = make_item()  # don't track — we're deleting it
    item_id = item["itemId"]
    del_resp = requests.delete(f"{BASE_URL}/entries/{item_id}", headers=HEADERS)
    assert del_resp.status_code in (200, 204)  # API returns 200

    get_resp = requests.get(f"{BASE_URL}/entries/{item_id}", headers=HEADERS)
    assert get_resp.status_code == 404


def test_user_isolation(cleanup_items):
    """User B cannot access User A's items."""
    item = make_item(track=cleanup_items)
    other_headers = {"X-User-Id": "other-user-" + uuid.uuid4().hex[:8]}
    resp = requests.get(f"{BASE_URL}/entries/{item['itemId']}", headers=other_headers)
    assert resp.status_code == 404


def test_count_endpoint(cleanup_items):
    make_item(title="Count Test 1", track=cleanup_items)
    make_item(title="Count Test 2", track=cleanup_items)
    resp = requests.get(f"{BASE_URL}/entries/count", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 2
