import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError


class WorkflowError(Exception):
    pass


class EntryNotFoundError(WorkflowError):
    pass


class RateLimitExceededError(WorkflowError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def entry_lookup_sk(entry_id: str) -> str:
    return f"ENTRYID#{entry_id}"


def rate_limit_sk(window_bucket: int) -> str:
    return f"AIRATE#{window_bucket}"


def get_entry(table: Any, user_id: str, entry_id: str) -> Dict[str, Any]:
    pk = user_pk(user_id)
    lookup = table.get_item(Key={"PK": pk, "SK": entry_lookup_sk(entry_id)}).get("Item")
    if not lookup:
        raise EntryNotFoundError("entry lookup missing")

    entry = table.get_item(Key={"PK": pk, "SK": lookup.get("entrySk", "")}).get("Item")
    if not entry:
        raise EntryNotFoundError("entry item missing")
    if entry.get("deletedAt"):
        raise EntryNotFoundError("entry deleted")
    return entry


def mark_processing(table: Any, entry: Dict[str, Any]) -> None:
    table.update_item(
        Key={"PK": entry["PK"], "SK": entry["SK"]},
        UpdateExpression="SET aiStatus = :status, aiError = :error, updatedAt = :updatedAt",
        ExpressionAttributeValues={
            ":status": "PROCESSING",
            ":error": None,
            ":updatedAt": now_iso(),
        },
    )


def mark_complete(table: Any, entry: Dict[str, Any], summary: str, tags: list[str]) -> None:
    ts = now_iso()
    table.update_item(
        Key={"PK": entry["PK"], "SK": entry["SK"]},
        UpdateExpression=(
            "SET aiStatus = :status, summary = :summary, tags = :tags, "
            "aiUpdatedAt = :aiUpdatedAt, aiError = :error, updatedAt = :updatedAt"
        ),
        ExpressionAttributeValues={
            ":status": "COMPLETE",
            ":summary": summary,
            ":tags": tags,
            ":aiUpdatedAt": ts,
            ":error": None,
            ":updatedAt": ts,
        },
    )


def mark_failed(table: Any, entry: Dict[str, Any], error_message: str) -> None:
    table.update_item(
        Key={"PK": entry["PK"], "SK": entry["SK"]},
        UpdateExpression="SET aiStatus = :status, aiError = :error, updatedAt = :updatedAt",
        ExpressionAttributeValues={
            ":status": "FAILED",
            ":error": error_message,
            ":updatedAt": now_iso(),
        },
    )


def check_rate_limit(table: Any, user_id: str, max_requests: int, window_seconds: int) -> None:
    if max_requests <= 0 or window_seconds <= 0:
        return

    now_epoch = int(time.time())
    window_bucket = now_epoch // window_seconds
    ttl = now_epoch + (window_seconds * 2)

    try:
        table.update_item(
            Key={"PK": user_pk(user_id), "SK": rate_limit_sk(window_bucket)},
            UpdateExpression=(
                "SET entityType = :entityType, expiresAt = :ttl, updatedAt = :updatedAt "
                "ADD requestCount :inc"
            ),
            ConditionExpression="attribute_not_exists(requestCount) OR requestCount < :maxRequests",
            ExpressionAttributeValues={
                ":entityType": "AI_RATE_LIMIT",
                ":ttl": ttl,
                ":updatedAt": now_iso(),
                ":inc": 1,
                ":maxRequests": max_requests,
            },
        )
    except ClientError as exc:
        code = (exc.response.get("Error") or {}).get("Code")
        if code == "ConditionalCheckFailedException":
            raise RateLimitExceededError("rate limit exceeded") from exc
        raise
