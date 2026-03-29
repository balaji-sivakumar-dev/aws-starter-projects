"""
Period insights handlers — framework-agnostic.

Generates AI-powered period summaries (weekly / monthly / yearly) by
fetching all entries in a date range, calling the LLM provider, and
persisting the result as a PERIOD_SUMMARY item in DynamoDB.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from . import repository
from .models import AppError


# ── Period date-range helpers ─────────────────────────────────────────────────

def _week_range(year: int, week: int):
    """Return (start_date, end_date, label) for an ISO calendar week."""
    try:
        start = date.fromisocalendar(year, week, 1)  # Monday
    except ValueError as exc:
        raise AppError(400, "VALIDATION_ERROR", str(exc)) from exc
    end = start + timedelta(days=6)  # Sunday
    return start.isoformat(), end.isoformat(), f"Week {week}, {year}"


def _month_range(year: int, month: int):
    """Return (start_date, end_date, label) for a calendar month."""
    if not 1 <= month <= 12:
        raise AppError(400, "VALIDATION_ERROR", "month must be between 1 and 12")
    start = date(year, month, 1)
    # First day of next month minus one day
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    label = start.strftime("%B %Y")
    return start.isoformat(), end.isoformat(), label


def _year_range(year: int):
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    return start.isoformat(), end.isoformat(), str(year)


# ── Public handlers ───────────────────────────────────────────────────────────

def generate_summary(
    user_id: str,
    period: str,
    year: int,
    week: Optional[int] = None,
    month: Optional[int] = None,
    provider_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a period summary:
      1. Calculate date range from period + year + week/month
      2. Fetch all entries in that range
      3. Call LLM analyze_period() if LLM_PROVIDER is set
      4. Persist result and return it

    Returns the summary item (aiStatus=DONE or ERROR).
    Raises AppError(400) for invalid input or no entries found.
    """
    period = period.lower().strip()

    if period == "weekly":
        if week is None:
            raise AppError(400, "VALIDATION_ERROR", "week is required for weekly period")
        start_date, end_date, label = _week_range(year, week)
        week_val = week
        month_val = None
    elif period == "monthly":
        if month is None:
            raise AppError(400, "VALIDATION_ERROR", "month is required for monthly period")
        start_date, end_date, label = _month_range(year, month)
        week_val = None
        month_val = month
    elif period == "yearly":
        start_date, end_date, label = _year_range(year)
        week_val = None
        month_val = None
    else:
        raise AppError(400, "VALIDATION_ERROR", "period must be weekly | monthly | yearly")

    # Fetch entries for the period
    entries = repository.get_items_in_range(user_id, start_date, end_date)
    if not entries:
        raise AppError(
            404,
            "NO_ENTRIES",
            f"No items found for {label} ({start_date} to {end_date}). "
            "Write some entries first.",
        )

    # Create the placeholder item
    item = repository.create_summary(
        user_id=user_id,
        period=period,
        period_label=label,
        year=year,
        start_date=start_date,
        end_date=end_date,
        week=week_val,
        month=month_val,
    )
    summary_id = item["summaryId"]

    # Run AI (synchronous)
    llm_provider = provider_name or os.getenv("LLM_PROVIDER", "")
    if llm_provider:
        _run_llm(user_id, summary_id, entries, label, provider_name=llm_provider)
    else:
        # No LLM: generate a basic text-only summary without AI
        _run_text_only(user_id, summary_id, entries, label)

    updated = repository.get_summary_item(user_id, summary_id)
    return repository.to_summary(updated)  # type: ignore[arg-type]


def list_summaries(user_id: str) -> List[Dict[str, Any]]:
    items = repository.list_summaries(user_id)
    # Sort newest-created first (UUID ordering is not time-ordered)
    return sorted(items, key=lambda x: x["createdAt"], reverse=True)


def get_summary(user_id: str, summary_id: str) -> Dict[str, Any]:
    item = repository.get_summary_item(user_id, summary_id)
    if not item:
        raise AppError(404, "NOT_FOUND", "summary not found")
    return repository.to_summary(item)


def delete_summary(user_id: str, summary_id: str) -> None:
    ok = repository.delete_summary(user_id, summary_id)
    if not ok:
        raise AppError(404, "NOT_FOUND", "summary not found")


def regenerate_summary(
    user_id: str, summary_id: str, provider_name: Optional[str] = None,
) -> Dict[str, Any]:
    item = repository.get_summary_item(user_id, summary_id)
    if not item:
        raise AppError(404, "NOT_FOUND", "summary not found")

    entries = repository.get_items_in_range(
        user_id, item["startDate"], item["endDate"]
    )
    if not entries:
        raise AppError(
            404,
            "NO_ENTRIES",
            f"No entries found for {item['periodLabel']}. "
            "Nothing to regenerate.",
        )

    # Reset to PROCESSING
    repository._table().update_item(
        Key={"PK": repository.user_pk(user_id), "SK": repository.summary_sk(summary_id)},
        UpdateExpression="SET aiStatus = :s, updatedAt = :u",
        ExpressionAttributeValues={":s": "PROCESSING", ":u": repository.now_iso()},
    )

    llm_provider = provider_name or os.getenv("LLM_PROVIDER", "")
    if llm_provider:
        _run_llm(user_id, summary_id, entries, item["periodLabel"], provider_name=llm_provider)
    else:
        _run_text_only(user_id, summary_id, entries, item["periodLabel"])

    updated = repository.get_summary_item(user_id, summary_id)
    return repository.to_summary(updated)  # type: ignore[arg-type]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _run_llm(
    user_id: str,
    summary_id: str,
    entries: List[Dict[str, Any]],
    period_label: str,
    provider_name: Optional[str] = None,
) -> None:
    from ..llm.factory import get_provider

    try:
        provider = get_provider(provider_name)
        result = provider.analyze_period(entries, period_label)
        repository.update_summary_result(
            user_id=user_id,
            summary_id=summary_id,
            entry_count=len(entries),
            narrative=result.get("narrative", ""),
            themes=result.get("themes", []),
            mood=result.get("mood", ""),
            highlights=result.get("highlights", []),
            reflection=result.get("reflection", ""),
        )
    except Exception as exc:
        repository.update_summary_error(user_id, summary_id, str(exc))
        raise AppError(502, "AI_ERROR", f"AI analysis failed: {exc}") from exc


def _run_text_only(
    user_id: str,
    summary_id: str,
    entries: List[Dict[str, Any]],
    period_label: str,
) -> None:
    """Basic non-AI summary: aggregates entry titles as a plain list."""
    titles = [e["title"] for e in entries]
    narrative = (
        f"You wrote {len(entries)} {'item' if len(entries) == 1 else 'items'} "
        f"during {period_label}:\n\n"
        + "\n".join(f"• {t}" for t in titles)
        + "\n\nSet LLM_PROVIDER to enable AI-generated insights."
    )
    repository.update_summary_result(
        user_id=user_id,
        summary_id=summary_id,
        entry_count=len(entries),
        narrative=narrative,
        themes=[],
        mood="",
        highlights=titles[:3],
        reflection="",
    )
