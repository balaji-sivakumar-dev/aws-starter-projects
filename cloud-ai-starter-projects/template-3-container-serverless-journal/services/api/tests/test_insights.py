"""
Integration tests — AI Insights (period summaries) endpoints.

Strategy
--------
- Stub LLMProvider injected via factory._instance (no real LLM calls).
- Entries are created via the /entries endpoint to ensure real DynamoDB data.
- Tests cover: generate, list, get, delete, regenerate, user isolation,
  error paths, and the text-only fallback when LLM_PROVIDER is unset.
"""

import os
from typing import Any, Dict, List
from datetime import date, timedelta

import pytest

from src.llm import factory
from src.llm.interface import LLMProvider


# ── Stub providers ────────────────────────────────────────────────────────────


class _StubPeriodProvider(LLMProvider):
    """Returns fixed period analysis — no network call."""

    RESULT: Dict[str, Any] = {
        "narrative": "A productive period of reflection and growth.",
        "themes": ["growth", "reflection", "work"],
        "mood": "positive and engaged",
        "highlights": ["Project launch", "Team meeting"],
        "reflection": "What would you do differently next week?",
    }

    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        return {"summary": "stub", "tags": []}

    def analyze_period(self, entries: List[Dict[str, Any]], period_label: str) -> Dict[str, Any]:
        return self.RESULT


class _FailingPeriodProvider(LLMProvider):
    """Always raises — used to test the error path."""

    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        return {"summary": "stub", "tags": []}

    def analyze_period(self, entries: List[Dict[str, Any]], period_label: str) -> Dict[str, Any]:
        raise RuntimeError("period analysis failed")


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_factory():
    factory.reset_provider()
    yield
    factory.reset_provider()
    os.environ.pop("LLM_PROVIDER", None)


def _inject(stub: LLMProvider):
    factory._instance = stub


# ── Helper: create entries with specific dates ─────────────────────────────────


def _make_entry(client, title: str, body: str = "test body", user: str = "dev-user"):
    resp = client.post(
        "/entries",
        json={"title": title, "body": body},
        headers={"X-User-Id": user},
    )
    assert resp.status_code == 201
    return resp.json()["item"]


# ── Generate summary (POST /insights/summaries) ───────────────────────────────


def test_generate_weekly_summary_returns_201(client):
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()

    _make_entry(client, "Entry this week")

    resp = client.post(
        "/insights/summaries",
        json={"period": "weekly", "year": iso_year, "week": iso_week},
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 201
    item = resp.json()["item"]
    assert item["period"] == "weekly"
    assert item["aiStatus"] == "DONE"
    assert item["narrative"] == _StubPeriodProvider.RESULT["narrative"]
    assert item["themes"] == _StubPeriodProvider.RESULT["themes"]
    assert item["mood"] == _StubPeriodProvider.RESULT["mood"]
    assert item["highlights"] == _StubPeriodProvider.RESULT["highlights"]
    assert item["reflection"] == _StubPeriodProvider.RESULT["reflection"]
    assert item["entryCount"] == 1


def test_generate_monthly_summary_returns_201(client):
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    _make_entry(client, "Monthly entry")

    resp = client.post(
        "/insights/summaries",
        json={"period": "monthly", "year": today.year, "month": today.month},
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 201
    item = resp.json()["item"]
    assert item["period"] == "monthly"
    assert item["aiStatus"] == "DONE"
    assert item["month"] == today.month
    assert item["year"] == today.year


def test_generate_yearly_summary_returns_201(client):
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    _make_entry(client, "Yearly entry")

    resp = client.post(
        "/insights/summaries",
        json={"period": "yearly", "year": today.year},
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 201
    item = resp.json()["item"]
    assert item["period"] == "yearly"
    assert item["aiStatus"] == "DONE"


def test_generate_summary_text_only_when_no_llm_provider(client):
    """When LLM_PROVIDER is unset, a text-only summary should be created."""
    os.environ.pop("LLM_PROVIDER", None)

    today = date.today()
    _make_entry(client, "Text-only entry")

    resp = client.post(
        "/insights/summaries",
        json={"period": "monthly", "year": today.year, "month": today.month},
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 201
    item = resp.json()["item"]
    assert item["aiStatus"] == "DONE"
    assert "Text-only entry" in item["narrative"]
    assert "Set LLM_PROVIDER" in item["narrative"]


def test_generate_summary_404_when_no_entries(client):
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    resp = client.post(
        "/insights/summaries",
        json={"period": "yearly", "year": 2000},
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NO_ENTRIES"


def test_generate_summary_400_for_invalid_period(client):
    resp = client.post(
        "/insights/summaries",
        json={"period": "hourly", "year": 2026},
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 422  # Pydantic Literal validation


def test_generate_summary_400_missing_week_for_weekly(client):
    _make_entry(client, "Entry")
    resp = client.post(
        "/insights/summaries",
        json={"period": "weekly", "year": 2026},
        headers={"X-User-Id": "dev-user"},
    )
    # week is None → core raises AppError(400, VALIDATION_ERROR)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_generate_summary_llm_error_returns_502(client):
    _inject(_FailingPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    _make_entry(client, "Doomed entry")

    resp = client.post(
        "/insights/summaries",
        json={"period": "monthly", "year": today.year, "month": today.month},
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 502
    assert resp.json()["detail"]["code"] == "AI_ERROR"


def test_generate_summary_response_includes_request_id(client):
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    _make_entry(client, "ID check entry")

    resp = client.post(
        "/insights/summaries",
        json={"period": "monthly", "year": today.year, "month": today.month},
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 201
    assert "requestId" in resp.json()


# ── List summaries (GET /insights/summaries) ──────────────────────────────────


def test_list_summaries_empty_initially(client):
    resp = client.get("/insights/summaries", headers={"X-User-Id": "dev-user"})
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_list_summaries_returns_created_summaries(client):
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    _make_entry(client, "Listed entry")

    client.post(
        "/insights/summaries",
        json={"period": "monthly", "year": today.year, "month": today.month},
        headers={"X-User-Id": "dev-user"},
    )

    resp = client.get("/insights/summaries", headers={"X-User-Id": "dev-user"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_list_summaries_user_isolation(client):
    """User B cannot see User A's summaries."""
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    _make_entry(client, "User A entry", user="user-a")

    client.post(
        "/insights/summaries",
        json={"period": "monthly", "year": today.year, "month": today.month},
        headers={"X-User-Id": "user-a"},
    )

    resp = client.get("/insights/summaries", headers={"X-User-Id": "user-b"})
    assert resp.json()["items"] == []


# ── Get summary (GET /insights/summaries/{id}) ────────────────────────────────


def test_get_summary_returns_correct_item(client):
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    _make_entry(client, "Get test entry")

    create_resp = client.post(
        "/insights/summaries",
        json={"period": "monthly", "year": today.year, "month": today.month},
        headers={"X-User-Id": "dev-user"},
    )
    summary_id = create_resp.json()["item"]["summaryId"]

    resp = client.get(f"/insights/summaries/{summary_id}", headers={"X-User-Id": "dev-user"})
    assert resp.status_code == 200
    assert resp.json()["item"]["summaryId"] == summary_id


def test_get_summary_404_for_nonexistent(client):
    resp = client.get(
        "/insights/summaries/00000000-0000-0000-0000-000000000000",
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 404


def test_get_summary_user_isolation(client):
    """User B cannot get User A's summary."""
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    _make_entry(client, "Private summary", user="user-a")

    create_resp = client.post(
        "/insights/summaries",
        json={"period": "monthly", "year": today.year, "month": today.month},
        headers={"X-User-Id": "user-a"},
    )
    summary_id = create_resp.json()["item"]["summaryId"]

    resp = client.get(f"/insights/summaries/{summary_id}", headers={"X-User-Id": "user-b"})
    assert resp.status_code == 404


# ── Delete summary (DELETE /insights/summaries/{id}) ─────────────────────────


def test_delete_summary_removes_item(client):
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    _make_entry(client, "To delete")

    create_resp = client.post(
        "/insights/summaries",
        json={"period": "monthly", "year": today.year, "month": today.month},
        headers={"X-User-Id": "dev-user"},
    )
    summary_id = create_resp.json()["item"]["summaryId"]

    del_resp = client.delete(
        f"/insights/summaries/{summary_id}", headers={"X-User-Id": "dev-user"}
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    get_resp = client.get(
        f"/insights/summaries/{summary_id}", headers={"X-User-Id": "dev-user"}
    )
    assert get_resp.status_code == 404


def test_delete_summary_404_for_nonexistent(client):
    resp = client.delete(
        "/insights/summaries/00000000-0000-0000-0000-000000000000",
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 404


# ── Regenerate summary (POST /insights/summaries/{id}/regenerate) ─────────────


def test_regenerate_summary_returns_updated_item(client):
    _inject(_StubPeriodProvider())
    os.environ["LLM_PROVIDER"] = "stub"

    today = date.today()
    _make_entry(client, "Regenerate me")

    create_resp = client.post(
        "/insights/summaries",
        json={"period": "monthly", "year": today.year, "month": today.month},
        headers={"X-User-Id": "dev-user"},
    )
    summary_id = create_resp.json()["item"]["summaryId"]

    regen_resp = client.post(
        f"/insights/summaries/{summary_id}/regenerate",
        headers={"X-User-Id": "dev-user"},
    )
    assert regen_resp.status_code == 200
    item = regen_resp.json()["item"]
    assert item["aiStatus"] == "DONE"
    assert item["summaryId"] == summary_id


def test_regenerate_summary_404_for_nonexistent(client):
    resp = client.post(
        "/insights/summaries/00000000-0000-0000-0000-000000000000/regenerate",
        headers={"X-User-Id": "dev-user"},
    )
    assert resp.status_code == 404
