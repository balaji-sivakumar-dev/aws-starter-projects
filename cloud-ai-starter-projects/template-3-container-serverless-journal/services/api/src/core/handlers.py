"""
Core business-logic handlers — framework-agnostic.

Each function takes plain Python arguments and returns plain dicts.
On validation or not-found errors they raise AppError, which adapters
(FastAPI, Lambda) catch and convert to their own error format.

Adding a new feature? Add it here first, then wire it in both adapters.
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


# ── Entries ───────────────────────────────────────────────────────────────────

def create_entry(user_id: str, title: str, body: str) -> Dict[str, Any]:
    title = title.strip()
    body = body.strip()
    if not title:
        raise AppError(400, "VALIDATION_ERROR", "title is required")
    if not body:
        raise AppError(400, "VALIDATION_ERROR", "body is required")
    item = repository.create_entry(user_id, title, body)
    return repository.to_entry(item)


def get_entry(user_id: str, entry_id: str) -> Dict[str, Any]:
    item = repository.resolve_entry(user_id, entry_id)
    if not item:
        raise AppError(404, "NOT_FOUND", "entry not found")
    return repository.to_entry(item)


def list_entries(
    user_id: str, limit: int, next_token: Optional[str]
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        items, tok = repository.list_entries(user_id, limit, next_token)
    except ValueError as exc:
        raise AppError(400, "VALIDATION_ERROR", str(exc)) from exc
    return items, tok


def update_entry(
    user_id: str,
    entry_id: str,
    title: Optional[str],
    body: Optional[str],
) -> Dict[str, Any]:
    if title is not None and not title.strip():
        raise AppError(400, "VALIDATION_ERROR", "title cannot be empty")
    if body is not None and not body.strip():
        raise AppError(400, "VALIDATION_ERROR", "body cannot be empty")
    if title is None and body is None:
        raise AppError(400, "VALIDATION_ERROR", "nothing to update")

    updated = repository.update_entry(
        user_id,
        entry_id,
        title.strip() if title else None,
        body.strip() if body else None,
    )
    if not updated:
        raise AppError(404, "NOT_FOUND", "entry not found")
    return repository.to_entry(updated)


def delete_entry(user_id: str, entry_id: str) -> None:
    ok = repository.soft_delete_entry(user_id, entry_id)
    if not ok:
        raise AppError(404, "NOT_FOUND", "entry not found")


# ── AI workflow ───────────────────────────────────────────────────────────────

def trigger_ai(user_id: str, entry_id: str) -> Dict[str, Any]:
    """
    Kick off AI enrichment (summary + tags) for an entry.

    Phase 1 (local): calls the LLM provider synchronously and writes results
                     back to DynamoDB directly.
    Phase 4 (AWS):   starts a Step Functions execution asynchronously.
    """
    item = repository.resolve_entry(user_id, entry_id)
    if not item:
        raise AppError(404, "NOT_FOUND", "entry not found")

    # Determine execution mode
    import os
    app_env = os.getenv("APP_ENV", "local")
    llm_provider = os.getenv("LLM_PROVIDER", "")

    if llm_provider:
        # LLM provider configured — call synchronously (Phase 3: LLM testing)
        return _run_ai_sync(user_id, entry_id, item, app_env)

    # No LLM configured yet — return stub
    return {
        "entryId": entry_id,
        "aiStatus": "SKIPPED",
        "note": "Set LLM_PROVIDER env var to enable AI enrichment (ollama | groq | openai)",
    }


def _run_ai_sync(
    user_id: str, entry_id: str, item: Dict[str, Any], app_env: str
) -> Dict[str, Any]:
    """Synchronous AI call — used in local/dev mode and for LLM testing."""
    from ..llm.factory import get_provider

    # Mark as processing
    repository._table().update_item(
        Key={"PK": item["PK"], "SK": item["SK"]},
        UpdateExpression="SET aiStatus = :s, updatedAt = :u",
        ExpressionAttributeValues={
            ":s": "PROCESSING",
            ":u": repository.now_iso(),
        },
    )

    try:
        provider = get_provider()
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
        return {"entryId": entry_id, "aiStatus": "DONE", **result}

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
