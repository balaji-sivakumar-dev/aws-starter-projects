"""
Integration tests — journal entry CRUD endpoints.

All tests use the `client` fixture from conftest.py which provides a FastAPI
TestClient backed by a fresh moto DynamoDB table.  No real AWS or Docker
container is required.
"""

import pytest

LOCAL_HEADERS = {"X-User-Id": "dev-user"}


# ── Helpers ───────────────────────────────────────────────────────────────────


def create_entry(client, title="Test Title", body="Test body text."):
    resp = client.post(
        "/entries",
        json={"title": title, "body": body},
        headers=LOCAL_HEADERS,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["item"]


# ── Health ────────────────────────────────────────────────────────────────────


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── /me ───────────────────────────────────────────────────────────────────────


def test_me_local_bypass(client):
    resp = client.get("/me", headers={"X-User-Id": "alice"})
    assert resp.status_code == 200
    assert resp.json()["userId"] == "alice"


def test_me_default_user_when_header_missing(client):
    resp = client.get("/me")
    assert resp.status_code == 200
    assert resp.json()["userId"] == "dev-user"


# ── CREATE ────────────────────────────────────────────────────────────────────


def test_create_entry(client):
    resp = client.post(
        "/entries",
        json={"title": "Hello World", "body": "First entry!"},
        headers=LOCAL_HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    item = data["item"]
    assert item["title"] == "Hello World"
    assert item["body"] == "First entry!"
    assert item["userId"] == "dev-user"
    assert item["aiStatus"] == "NOT_REQUESTED"
    assert item["tags"] == []
    assert "entryId" in item
    assert "requestId" in data


def test_create_entry_missing_title_returns_422(client):
    resp = client.post(
        "/entries",
        json={"body": "No title here"},
        headers=LOCAL_HEADERS,
    )
    assert resp.status_code == 422


def test_create_entry_missing_body_returns_422(client):
    resp = client.post(
        "/entries",
        json={"title": "No body"},
        headers=LOCAL_HEADERS,
    )
    assert resp.status_code == 422


# ── LIST ──────────────────────────────────────────────────────────────────────


def test_list_entries_empty(client):
    resp = client.get("/entries", headers=LOCAL_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["nextToken"] is None


def test_list_entries_returns_created_items(client):
    create_entry(client, title="Entry A")
    create_entry(client, title="Entry B")

    resp = client.get("/entries", headers=LOCAL_HEADERS)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    titles = {i["title"] for i in items}
    assert titles == {"Entry A", "Entry B"}


def test_list_entries_user_isolation(client):
    """Entries created by one user are not visible to another."""
    create_entry(client, title="Alice entry")
    resp = client.get("/entries", headers={"X-User-Id": "bob"})
    assert resp.json()["items"] == []


def test_list_entries_pagination(client):
    for i in range(5):
        create_entry(client, title=f"Entry {i}")

    # First page: 3 items
    resp1 = client.get("/entries?limit=3", headers=LOCAL_HEADERS)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["items"]) == 3
    assert data1["nextToken"] is not None

    # Second page: remaining 2 items
    resp2 = client.get(
        f"/entries?limit=3&nextToken={data1['nextToken']}",
        headers=LOCAL_HEADERS,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 2
    assert data2["nextToken"] is None


# ── GET (single) ──────────────────────────────────────────────────────────────


def test_get_entry(client):
    item = create_entry(client)
    entry_id = item["entryId"]

    resp = client.get(f"/entries/{entry_id}", headers=LOCAL_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["item"]["entryId"] == entry_id


def test_get_entry_not_found(client):
    resp = client.get("/entries/nonexistent-id-1234", headers=LOCAL_HEADERS)
    assert resp.status_code == 404


def test_get_entry_other_user_cannot_see(client):
    item = create_entry(client)
    entry_id = item["entryId"]

    resp = client.get(f"/entries/{entry_id}", headers={"X-User-Id": "eve"})
    assert resp.status_code == 404


# ── UPDATE ────────────────────────────────────────────────────────────────────


def test_update_entry_title_and_body(client):
    item = create_entry(client)
    entry_id = item["entryId"]

    resp = client.put(
        f"/entries/{entry_id}",
        json={"title": "New Title", "body": "New body."},
        headers=LOCAL_HEADERS,
    )
    assert resp.status_code == 200
    updated = resp.json()["item"]
    assert updated["title"] == "New Title"
    assert updated["body"] == "New body."


def test_update_entry_title_only(client):
    item = create_entry(client, body="Original body")
    entry_id = item["entryId"]

    resp = client.put(
        f"/entries/{entry_id}",
        json={"title": "Changed Title"},
        headers=LOCAL_HEADERS,
    )
    assert resp.status_code == 200
    updated = resp.json()["item"]
    assert updated["title"] == "Changed Title"
    assert updated["body"] == "Original body"


def test_update_entry_not_found(client):
    resp = client.put(
        "/entries/nonexistent-id-5678",
        json={"title": "Ghost"},
        headers=LOCAL_HEADERS,
    )
    assert resp.status_code == 404


# ── DELETE ────────────────────────────────────────────────────────────────────


def test_delete_entry(client):
    item = create_entry(client)
    entry_id = item["entryId"]

    resp = client.delete(f"/entries/{entry_id}", headers=LOCAL_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Deleted entry should no longer appear in list or GET
    list_resp = client.get("/entries", headers=LOCAL_HEADERS)
    assert list_resp.json()["items"] == []

    get_resp = client.get(f"/entries/{entry_id}", headers=LOCAL_HEADERS)
    assert get_resp.status_code == 404


def test_delete_entry_not_found(client):
    resp = client.delete("/entries/nonexistent-id-9999", headers=LOCAL_HEADERS)
    assert resp.status_code == 404


# ── GET /entries/count ─────────────────────────────────────────────────────────


def test_count_returns_zero_when_no_entries(client):
    resp = client.get("/entries/count", headers=LOCAL_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_count_returns_correct_number(client):
    for i in range(3):
        create_entry(client, title=f"Entry {i}")
    resp = client.get("/entries/count", headers=LOCAL_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["count"] == 3


def test_count_excludes_deleted_entries(client):
    create_entry(client, title="Keep me")
    e2 = create_entry(client, title="Delete me")
    client.delete(f"/entries/{e2['entryId']}", headers=LOCAL_HEADERS)
    resp = client.get("/entries/count", headers=LOCAL_HEADERS)
    assert resp.json()["count"] == 1


def test_count_user_isolation(client):
    create_entry(client, title="User A entry")
    resp = client.get("/entries/count", headers={"X-User-Id": "user-b"})
    assert resp.json()["count"] == 0


def test_count_response_includes_request_id(client):
    resp = client.get("/entries/count", headers=LOCAL_HEADERS)
    assert "requestId" in resp.json()


# ── POST /entries/bulk-delete ──────────────────────────────────────────────────


def test_bulk_delete_removes_specified_entries(client):
    e1 = create_entry(client, title="Delete 1")
    e2 = create_entry(client, title="Delete 2")
    e3 = create_entry(client, title="Keep me")

    resp = client.post(
        "/entries/bulk-delete",
        json={"entryIds": [e1["entryId"], e2["entryId"]]},
        headers=LOCAL_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 2

    assert client.get(f"/entries/{e3['entryId']}", headers=LOCAL_HEADERS).status_code == 200
    assert client.get(f"/entries/{e1['entryId']}", headers=LOCAL_HEADERS).status_code == 404
    assert client.get(f"/entries/{e2['entryId']}", headers=LOCAL_HEADERS).status_code == 404


def test_bulk_delete_skips_nonexistent_ids(client):
    e1 = create_entry(client, title="Real entry")
    resp = client.post(
        "/entries/bulk-delete",
        json={"entryIds": [e1["entryId"], "00000000-0000-0000-0000-000000000000"]},
        headers=LOCAL_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 1


def test_bulk_delete_empty_list_returns_400(client):
    resp = client.post(
        "/entries/bulk-delete",
        json={"entryIds": []},
        headers=LOCAL_HEADERS,
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_bulk_delete_user_isolation(client):
    """User B bulk-deleting User A's entry IDs deletes 0 entries."""
    e1 = create_entry(client, title="User A private")
    resp = client.post(
        "/entries/bulk-delete",
        json={"entryIds": [e1["entryId"]]},
        headers={"X-User-Id": "user-b"},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 0
    # Entry still exists for the original user
    assert client.get(f"/entries/{e1['entryId']}", headers=LOCAL_HEADERS).status_code == 200


def test_bulk_delete_response_includes_request_id(client):
    e1 = create_entry(client, title="Entry")
    resp = client.post(
        "/entries/bulk-delete",
        json={"entryIds": [e1["entryId"]]},
        headers=LOCAL_HEADERS,
    )
    assert "requestId" in resp.json()
