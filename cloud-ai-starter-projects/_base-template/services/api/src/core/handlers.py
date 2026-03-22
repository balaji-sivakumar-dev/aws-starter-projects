"""
Core business-logic handlers — framework-agnostic.

Each function takes plain Python arguments and returns plain dicts.
On validation or not-found errors they raise AppError, which adapters
(FastAPI, Lambda) catch and convert to their own error format.

Replace "item" with your domain entity name throughout this file.
"""

from typing import Any, Dict, List, Optional, Tuple

from . import repository
from .models import AppError


# ── Health ────────────────────────────────────────────────────────────────────

def health() -> Dict[str, str]:
    return {"status": "ok"}


# ── Identity ──────────────────────────────────────────────────────────────────

def me(user_id: str, email: str = "") -> Dict[str, Any]:
    import os
    app_env = os.getenv("APP_ENV", "local")
    if app_env in ("local", "test"):
        is_admin = True
    else:
        admin_emails = {
            e.strip().lower()
            for e in os.getenv("ADMIN_EMAILS", "").split(",")
            if e.strip()
        }
        is_admin = email.strip().lower() in admin_emails
    return {"userId": user_id, "email": email, "isAdmin": is_admin}


# ── Items ─────────────────────────────────────────────────────────────────────

def create_item(user_id: str, title: str, body: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    title = title.strip()
    body = body.strip()
    if not title:
        raise AppError(400, "VALIDATION_ERROR", "title is required")
    if not body:
        raise AppError(400, "VALIDATION_ERROR", "body is required")
    item = repository.create_item(user_id, title, body, data)
    return repository.to_item(item)


def get_item(user_id: str, item_id: str) -> Dict[str, Any]:
    item = repository.resolve_item(user_id, item_id)
    if not item:
        raise AppError(404, "NOT_FOUND", "item not found")
    return repository.to_item(item)


def list_items(
    user_id: str, limit: int, next_token: Optional[str]
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        items, tok = repository.list_items(user_id, limit, next_token)
    except ValueError as exc:
        raise AppError(400, "VALIDATION_ERROR", str(exc)) from exc
    return items, tok


def update_item(
    user_id: str,
    item_id: str,
    title: Optional[str],
    body: Optional[str],
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if title is not None and not title.strip():
        raise AppError(400, "VALIDATION_ERROR", "title cannot be empty")
    if body is not None and not body.strip():
        raise AppError(400, "VALIDATION_ERROR", "body cannot be empty")
    if title is None and body is None and data is None:
        raise AppError(400, "VALIDATION_ERROR", "nothing to update")

    updated = repository.update_item(
        user_id,
        item_id,
        title.strip() if title else None,
        body.strip() if body else None,
        data,
    )
    if not updated:
        raise AppError(404, "NOT_FOUND", "item not found")
    return repository.to_item(updated)


def delete_item(user_id: str, item_id: str) -> None:
    ok = repository.soft_delete_item(user_id, item_id)
    if not ok:
        raise AppError(404, "NOT_FOUND", "item not found")


def count_items(user_id: str) -> int:
    return repository.count_items(user_id)


def bulk_delete_items(user_id: str, item_ids: List[str]) -> int:
    if not item_ids:
        raise AppError(400, "VALIDATION_ERROR", "item_ids must not be empty")
    if len(item_ids) > 200:
        raise AppError(400, "VALIDATION_ERROR", "bulk delete limited to 200 items at a time")
    return repository.bulk_delete_items(user_id, item_ids)


# ── AI workflow ───────────────────────────────────────────────────────────────

def trigger_ai(
    user_id: str, item_id: str, provider_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Kick off AI enrichment (summary + tags) for an item."""
    item = repository.resolve_item(user_id, item_id)
    if not item:
        raise AppError(404, "NOT_FOUND", "item not found")

    import os
    llm_provider = provider_name or os.getenv("LLM_PROVIDER", "")

    if llm_provider:
        return _run_ai_sync(user_id, item_id, item, llm_provider)

    return {
        "itemId": item_id,
        "aiStatus": "SKIPPED",
        "note": "Set LLM_PROVIDER env var to enable AI enrichment (ollama | groq | openai | bedrock)",
    }


def _run_ai_sync(
    user_id: str, item_id: str, item: Dict[str, Any], provider_name: str,
) -> Dict[str, Any]:
    """Synchronous AI call — used in local/dev mode."""
    from ..llm.factory import get_provider

    repository._table().update_item(
        Key={"PK": item["PK"], "SK": item["SK"]},
        UpdateExpression="SET aiStatus = :s, updatedAt = :u",
        ExpressionAttributeValues={
            ":s": "PROCESSING",
            ":u": repository.now_iso(),
        },
    )

    try:
        provider = get_provider(provider_name)
        result = provider.enrich(title=item["title"], body=item["body"])

        repository._table().update_item(
            Key={"PK": item["PK"], "SK": item["SK"]},
            UpdateExpression=(
                "SET aiStatus = :s, summary = :sum, tags = :tags, "
                "aiUpdatedAt = :at, updatedAt = :u, aiError = :e"
            ),
            ExpressionAttributeValues={
                ":s": "DONE",
                ":sum": result.get("summary", ""),
                ":tags": result.get("tags", []),
                ":at": repository.now_iso(),
                ":u": repository.now_iso(),
                ":e": None,
            },
        )
        return {"itemId": item_id, "aiStatus": "DONE", **result}

    except Exception as exc:
        repository._table().update_item(
            Key={"PK": item["PK"], "SK": item["SK"]},
            UpdateExpression="SET aiStatus = :s, aiError = :e, updatedAt = :u",
            ExpressionAttributeValues={
                ":s": "ERROR",
                ":e": str(exc),
                ":u": repository.now_iso(),
            },
        )
        raise AppError(502, "AI_ERROR", f"AI enrichment failed: {exc}") from exc
