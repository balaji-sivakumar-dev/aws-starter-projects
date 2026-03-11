from datetime import datetime, timezone
from typing import Any, Dict, Optional

from errors import ApiError

ALLOWED_AI_STATUSES = {
    "NOT_REQUESTED",
    "QUEUED",
    "PROCESSING",
    "COMPLETE",
    "FAILED",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_create_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    title = str(payload.get("title", "")).strip()
    body = str(payload.get("body", "")).strip()

    if not title:
        raise ApiError(400, "VALIDATION_ERROR", "title is required")
    if not body:
        raise ApiError(400, "VALIDATION_ERROR", "body is required")

    return {"title": title, "body": body}


def validate_update_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    updates: Dict[str, str] = {}

    if "title" in payload:
        title = str(payload.get("title", "")).strip()
        if not title:
            raise ApiError(400, "VALIDATION_ERROR", "title cannot be empty")
        updates["title"] = title

    if "body" in payload:
        body = str(payload.get("body", "")).strip()
        if not body:
            raise ApiError(400, "VALIDATION_ERROR", "body cannot be empty")
        updates["body"] = body

    if not updates:
        raise ApiError(400, "VALIDATION_ERROR", "nothing to update")

    return updates


def to_entry_response(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "entryId": item["entryId"],
        "userId": item["userId"],
        "title": item["title"],
        "body": item["body"],
        "createdAt": item["createdAt"],
        "updatedAt": item["updatedAt"],
        "deletedAt": item.get("deletedAt"),
        "aiStatus": item.get("aiStatus", "NOT_REQUESTED"),
        "summary": item.get("summary"),
        "tags": item.get("tags", []),
        "aiUpdatedAt": item.get("aiUpdatedAt"),
        "aiError": item.get("aiError"),
    }


def to_limit(raw_limit: Optional[str]) -> int:
    if raw_limit is None:
        return 20
    try:
        value = int(raw_limit)
    except (TypeError, ValueError) as exc:
        raise ApiError(400, "VALIDATION_ERROR", "limit must be an integer") from exc

    if value < 1 or value > 100:
        raise ApiError(400, "VALIDATION_ERROR", "limit must be between 1 and 100")
    return value
