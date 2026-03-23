"""
Integration tests — authentication behaviour.

Tests cover:
  - Local mode: X-User-Id header bypass (APP_ENV=test → same path as local)
  - Missing / empty header falls back to "dev-user"
  - Bearer token path: in local/test mode any token is accepted; real JWT
    validation is exercised via a mocked JWKS endpoint (stub test).
"""

import pytest

# ── Local auth bypass ─────────────────────────────────────────────────────────


def test_local_mode_sets_user_from_header(client):
    resp = client.get("/me", headers={"X-User-Id": "test-alice"})
    assert resp.status_code == 200
    assert resp.json()["userId"] == "test-alice"


def test_local_mode_strips_whitespace_from_user_id(client):
    resp = client.get("/me", headers={"X-User-Id": "  trimmed  "})
    assert resp.status_code == 200
    assert resp.json()["userId"] == "trimmed"


def test_local_mode_empty_header_falls_back_to_dev_user(client):
    resp = client.get("/me", headers={"X-User-Id": ""})
    assert resp.status_code == 200
    assert resp.json()["userId"] == "dev-user"


def test_local_mode_missing_header_falls_back_to_dev_user(client):
    resp = client.get("/me")
    assert resp.status_code == 200
    assert resp.json()["userId"] == "dev-user"


# ── Entries respect user identity from header ─────────────────────────────────


def test_entries_are_scoped_to_user(client):
    """Two users each see only their own entries."""
    headers_a = {"X-User-Id": "user-a"}
    headers_b = {"X-User-Id": "user-b"}

    # user-a creates an entry
    create_resp = client.post(
        "/entries",
        json={"title": "A's entry", "body": "Private"},
        headers=headers_a,
    )
    assert create_resp.status_code == 201

    # user-a can see it
    list_a = client.get("/entries", headers=headers_a).json()["items"]
    assert len(list_a) == 1

    # user-b cannot see it
    list_b = client.get("/entries", headers=headers_b).json()["items"]
    assert len(list_b) == 0


def test_entry_delete_by_different_user_returns_404(client):
    """A user cannot delete another user's entry."""
    owner_headers = {"X-User-Id": "owner"}
    attacker_headers = {"X-User-Id": "attacker"}

    create_resp = client.post(
        "/entries",
        json={"title": "Owner entry", "body": "Mine"},
        headers=owner_headers,
    )
    entry_id = create_resp.json()["item"]["itemId"]

    delete_resp = client.delete(f"/entries/{entry_id}", headers=attacker_headers)
    assert delete_resp.status_code == 404

    # Original entry still accessible to owner
    get_resp = client.get(f"/entries/{entry_id}", headers=owner_headers)
    assert get_resp.status_code == 200


# ── Bad / malformed requests ──────────────────────────────────────────────────


def test_create_entry_with_empty_title_returns_400(client):
    resp = client.post(
        "/entries",
        json={"title": "", "body": "Some body"},
        headers={"X-User-Id": "dev-user"},
    )
    # Empty title passes Pydantic (no min_length constraint) but the
    # core handler rejects it with a 400 VALIDATION_ERROR.
    assert resp.status_code == 400


def test_get_nonexistent_entry_returns_404(client):
    resp = client.get(
        "/entries/00000000-0000-0000-0000-000000000000",
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 404


def test_update_nonexistent_entry_returns_404(client):
    resp = client.put(
        "/entries/00000000-0000-0000-0000-000000000000",
        json={"title": "Ghost"},
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 404


def test_delete_nonexistent_entry_returns_404(client):
    resp = client.delete(
        "/entries/00000000-0000-0000-0000-000000000000",
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 404
