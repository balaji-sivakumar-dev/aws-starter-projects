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

    def analyze_period(self, entries, period_label):
        return {"narrative": "", "themes": [], "mood": "", "highlights": [], "reflection": ""}


class _FailingProvider(LLMProvider):
    """Always raises — used to test the error path."""

    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        raise RuntimeError("provider unavailable")

    def analyze_period(self, entries, period_label):
        raise RuntimeError("provider unavailable")


# ── Fixture helpers ───────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_factory():
    """Ensure the cached provider is cleared before and after every test."""
    factory.reset_provider()
    yield
    factory.reset_provider()


def _inject(stub: LLMProvider, name: str = "stub"):
    """Inject a stub directly into the factory cache."""
    factory._cache[name] = stub


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
    entry_id = create.json()["item"]["itemId"]

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
    entry_id = create.json()["item"]["itemId"]

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
    entry_id = create.json()["item"]["itemId"]

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
    entry_id = create.json()["item"]["itemId"]

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
    entry_id = create.json()["item"]["itemId"]

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
    entry_id = create.json()["item"]["itemId"]

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
    entry_id = create.json()["item"]["itemId"]

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
    assert factory.get_provider("stub") is not None

    factory.reset_provider()
    assert len(factory._cache) == 0


# ── Provider selection via X-LLM-Provider header ─────────────────────────────


def test_trigger_ai_uses_provider_from_header(client):
    """The x-llm-provider header should select the provider."""
    _inject(_StubProvider(), name="stub")
    os.environ["LLM_PROVIDER"] = "stub"

    create = client.post(
        "/entries",
        json={"title": "Header Test", "body": "Using a specific provider."},
        headers={"X-User-Id": "dev-user"},
    )
    entry_id = create.json()["item"]["itemId"]

    resp = client.post(
        f"/entries/{entry_id}/ai",
        headers={"X-User-Id": "dev-user", "x-llm-provider": "stub"},
    )
    assert resp.status_code == 202
    assert resp.json()["aiStatus"] == "DONE"


# ── Config endpoint tests ────────────────────────────────────────────────────


def test_config_providers_returns_list(client):
    """GET /config/providers should return available providers."""
    os.environ["GROQ_API_KEY"] = "gsk_test"
    os.environ["LLM_PROVIDER"] = "groq"

    resp = client.get("/config/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert "default" in data
    assert data["default"] == "groq"
    names = [p["name"] for p in data["providers"]]
    assert "groq" in names


def test_config_providers_omits_unconfigured(client):
    """Providers without API keys should be excluded."""
    os.environ.pop("GROQ_API_KEY", None)
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ["LLM_PROVIDER"] = ""

    resp = client.get("/config/providers")
    data = resp.json()
    names = [p["name"] for p in data["providers"]]
    assert "groq" not in names
    assert "openai" not in names


# ── Multi-provider factory tests ─────────────────────────────────────────────


def test_factory_available_providers_with_keys():
    """available_providers() should return only providers with API keys set."""
    os.environ["GROQ_API_KEY"] = "gsk_test"
    os.environ.pop("OPENAI_API_KEY", None)

    providers = factory.available_providers()
    names = [p["name"] for p in providers]
    assert "groq" in names
    assert "openai" not in names


def test_factory_get_provider_by_name():
    """get_provider(name) should return a provider by name, caching it."""
    _inject(_StubProvider(), name="stub")
    p = factory.get_provider("stub")
    assert isinstance(p, _StubProvider)


# ── parse_period_response — JSON extraction robustness ───────────────────────


def test_parse_period_response_clean_json():
    """Correctly formed JSON is parsed normally."""
    raw = '{"narrative": "Good period.", "themes": ["growth"], "mood": "positive", "highlights": ["Launch"], "reflection": "Keep going?"}'
    result = LLMProvider.parse_period_response(raw)
    assert result["narrative"] == "Good period."
    assert result["themes"] == ["growth"]
    assert result["mood"] == "positive"
    assert result["highlights"] == ["Launch"]
    assert result["reflection"] == "Keep going?"


def test_parse_period_response_strips_markdown_fences():
    """Markdown code fences around JSON are stripped."""
    raw = '```json\n{"narrative": "Good.", "themes": [], "mood": "ok", "highlights": [], "reflection": ""}\n```'
    result = LLMProvider.parse_period_response(raw)
    assert result["narrative"] == "Good."


def test_parse_period_response_handles_prose_before_json():
    """LLM prose before the JSON block is ignored."""
    raw = 'Here is my analysis:\n\n{"narrative": "Productive.", "themes": ["work"], "mood": "focused", "highlights": [], "reflection": "Next steps?"}'
    result = LLMProvider.parse_period_response(raw)
    assert result["narrative"] == "Productive."
    assert result["themes"] == ["work"]


def test_parse_period_response_handles_prose_after_json():
    """LLM prose after the JSON block is ignored."""
    raw = '{"narrative": "Growth.", "themes": [], "mood": "good", "highlights": [], "reflection": ""}\n\nLet me know if you need more detail.'
    result = LLMProvider.parse_period_response(raw)
    assert result["narrative"] == "Growth."


def test_parse_period_response_fallback_on_bad_json():
    """When JSON cannot be extracted, the raw text is used as narrative fallback."""
    raw = "This is not JSON at all."
    result = LLMProvider.parse_period_response(raw)
    assert "This is not JSON at all" in result["narrative"]
    assert result["themes"] == []


def test_parse_response_clean_json():
    raw = '{"summary": "A good day.", "tags": ["health", "work"]}'
    result = LLMProvider.parse_response(raw)
    assert result["summary"] == "A good day."
    assert result["tags"] == ["health", "work"]


def test_parse_response_handles_prose_before_json():
    raw = 'Sure! Here is the result:\n{"summary": "Active day.", "tags": ["fitness"]}'
    result = LLMProvider.parse_response(raw)
    assert result["summary"] == "Active day."
    assert "fitness" in result["tags"]
