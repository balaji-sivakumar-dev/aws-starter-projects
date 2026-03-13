"""
Integration tests — LLM / AI enrichment endpoint.

Strategy
--------
Tests use a stub LLMProvider that replaces the real provider via
factory.reset_provider() + monkeypatching.  No real LLM API call is made.

This validates:
  - The full HTTP → handler → DynamoDB write flow for the happy path
  - Error propagation when the LLM provider raises
  - The SKIPPED stub response when LLM_PROVIDER is unset
  - factory.reset_provider() isolation between tests
"""

import os
from typing import Any, Dict
from unittest.mock import patch

import pytest

from src.llm import factory
from src.llm.interface import LLMProvider


# ── Stub provider ─────────────────────────────────────────────────────────────


class _StubProvider(LLMProvider):
    """Returns a fixed enrichment response — no network call."""

    RESULT: Dict[str, Any] = {
        "summary": "A stub summary for testing.",
        "tags": ["test", "stub"],
    }

    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        return self.RESULT


class _FailingProvider(LLMProvider):
    """Always raises — used to test the error path."""

    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        raise RuntimeError("provider unavailable")


# ── Fixture helpers ───────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_factory():
    """Ensure the cached provider is cleared before and after every test."""
    factory.reset_provider()
    yield
    factory.reset_provider()


def _inject(stub: LLMProvider):
    """Inject a stub directly into the factory cache."""
    factory._instance = stub


# ── Happy path ────────────────────────────────────────────────────────────────


def test_trigger_ai_returns_done_with_summary_and_tags(client):
    _inject(_StubProvider())
    os.environ["LLM_PROVIDER"] = "stub"   # non-empty → handler calls provider

    # Create an entry first
    create = client.post(
        "/entries",
        json={"title": "Mountain Hike", "body": "Went hiking today. Amazing views."},
        headers={"X-User-Id": "dev-user"},
    )
    entry_id = create.json()["item"]["entryId"]

    resp = client.post(f"/entries/{entry_id}/ai", headers={"X-User-Id": "dev-user"})
    assert resp.status_code == 202
    data = resp.json()
    assert data["aiStatus"] == "DONE"
    assert data["summary"] == _StubProvider.RESULT["summary"]
    assert data["tags"] == _StubProvider.RESULT["tags"]


def test_trigger_ai_persists_fields_in_dynamodb(client):
    """After a successful AI call the entry returned by GET reflects the update."""
    _inject(_StubProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    create = client.post(
        "/entries",
        json={"title": "Test Entry", "body": "Body text for AI."},
        headers={"X-User-Id": "dev-user"},
    )
    entry_id = create.json()["item"]["entryId"]

    client.post(f"/entries/{entry_id}/ai", headers={"X-User-Id": "dev-user"})

    get = client.get(f"/entries/{entry_id}", headers={"X-User-Id": "dev-user"})
    item = get.json()["item"]
    assert item["aiStatus"] == "DONE"
    assert item["summary"] == _StubProvider.RESULT["summary"]
    assert item["tags"] == _StubProvider.RESULT["tags"]
    assert item["aiUpdatedAt"] is not None


def test_trigger_ai_response_includes_request_id(client):
    _inject(_StubProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    create = client.post(
        "/entries",
        json={"title": "T", "body": "B"},
        headers={"X-User-Id": "dev-user"},
    )
    entry_id = create.json()["item"]["entryId"]

    resp = client.post(f"/entries/{entry_id}/ai", headers={"X-User-Id": "dev-user"})
    assert "requestId" in resp.json()


# ── Error path ────────────────────────────────────────────────────────────────


def test_trigger_ai_sets_error_status_when_provider_fails(client):
    _inject(_FailingProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    create = client.post(
        "/entries",
        json={"title": "Failing AI", "body": "This will fail."},
        headers={"X-User-Id": "dev-user"},
    )
    entry_id = create.json()["item"]["entryId"]

    resp = client.post(f"/entries/{entry_id}/ai", headers={"X-User-Id": "dev-user"})
    assert resp.status_code == 502


def test_trigger_ai_writes_error_to_dynamodb_on_failure(client):
    _inject(_FailingProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    create = client.post(
        "/entries",
        json={"title": "Failing AI", "body": "This will fail."},
        headers={"X-User-Id": "dev-user"},
    )
    entry_id = create.json()["item"]["entryId"]

    client.post(f"/entries/{entry_id}/ai", headers={"X-User-Id": "dev-user"})

    get = client.get(f"/entries/{entry_id}", headers={"X-User-Id": "dev-user"})
    item = get.json()["item"]
    assert item["aiStatus"] == "ERROR"
    assert "provider unavailable" in item["aiError"]


# ── SKIPPED stub (no LLM_PROVIDER set) ───────────────────────────────────────


def test_trigger_ai_returns_skipped_when_no_provider(client):
    os.environ.pop("LLM_PROVIDER", None)

    create = client.post(
        "/entries",
        json={"title": "No AI", "body": "LLM_PROVIDER is unset."},
        headers={"X-User-Id": "dev-user"},
    )
    entry_id = create.json()["item"]["entryId"]

    resp = client.post(f"/entries/{entry_id}/ai", headers={"X-User-Id": "dev-user"})
    assert resp.status_code == 202
    assert resp.json()["aiStatus"] == "SKIPPED"


# ── Not found ─────────────────────────────────────────────────────────────────


def test_trigger_ai_returns_404_for_nonexistent_entry(client):
    _inject(_StubProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    resp = client.post(
        "/entries/00000000-0000-0000-0000-000000000000/ai",
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 404


def test_trigger_ai_cannot_enrich_another_users_entry(client):
    _inject(_StubProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    create = client.post(
        "/entries",
        json={"title": "Owner's entry", "body": "Private."},
        headers={"X-User-Id": "owner"},
    )
    entry_id = create.json()["item"]["entryId"]

    # Attacker tries to enrich owner's entry
    resp = client.post(
        f"/entries/{entry_id}/ai",
        headers={"X-User-Id": "attacker"},
    )
    assert resp.status_code == 404


# ── factory.reset_provider ────────────────────────────────────────────────────


def test_factory_reset_allows_provider_swap(client):
    """Verify reset_provider() truly clears the cache."""
    _inject(_StubProvider())
    assert factory.get_provider() is not None

    factory.reset_provider()
    assert factory._instance is None
