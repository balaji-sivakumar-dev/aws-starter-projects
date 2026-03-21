"""
Audit logging — tracks user activity, AI calls, and RAG queries.

Audit records are stored in DynamoDB:
  PK: AUDIT#{YYYY-MM-DD}
  SK: {timestamp}#{eventId}

This allows efficient queries by date range for admin dashboards.
"""

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

TABLE_NAME = os.getenv("JOURNAL_TABLE_NAME", "journal")
AUDIT_ENABLED = os.getenv("AUDIT_ENABLED", "true").lower() == "true"


def _get_table():
    from .repository import _table
    return _table()


def log_event(
    event_type: str,
    user_id: str = "",
    details: dict | None = None,
) -> None:
    """Log an audit event to DynamoDB."""
    if not AUDIT_ENABLED:
        return

    now = datetime.now(timezone.utc)
    event_id = str(uuid.uuid4())[:8]
    ts = now.isoformat().replace("+00:00", "Z")
    date_key = now.strftime("%Y-%m-%d")

    item = {
        "PK": f"AUDIT#{date_key}",
        "SK": f"{ts}#{event_id}",
        "entityType": "AUDIT_EVENT",
        "eventType": event_type,
        "userId": user_id,
        "timestamp": ts,
        "details": _sanitize(details or {}),
    }

    try:
        _get_table().put_item(Item=item)
    except Exception as e:
        logger.error("Failed to write audit event: %s", e)


def log_ai_call(
    user_id: str,
    provider: str,
    model: str,
    task_type: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: int = 0,
    cost_estimate: float = 0.0,
) -> None:
    """Log an AI/LLM API call."""
    log_event(
        event_type="ai_call",
        user_id=user_id,
        details={
            "provider": provider,
            "model": model,
            "taskType": task_type,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "latencyMs": latency_ms,
            "costEstimate": cost_estimate,
        },
    )


def log_rag_query(
    user_id: str,
    query: str,
    results_count: int,
    answer_length: int = 0,
    latency_ms: int = 0,
) -> None:
    """Log a RAG query."""
    log_event(
        event_type="rag_query",
        user_id=user_id,
        details={
            "query": query[:200],
            "resultsCount": results_count,
            "answerLength": answer_length,
            "latencyMs": latency_ms,
        },
    )


def log_user_action(user_id: str, action: str, resource_id: str = "") -> None:
    """Log a user action (entry CRUD, login, etc.)."""
    log_event(
        event_type="user_action",
        user_id=user_id,
        details={"action": action, "resourceId": resource_id},
    )


def get_audit_logs(date: str, limit: int = 50, next_token: str | None = None) -> dict:
    """Query audit logs for a specific date."""
    import base64
    import json

    kwargs = {
        "KeyConditionExpression": "PK = :pk",
        "ExpressionAttributeValues": {":pk": f"AUDIT#{date}"},
        "ScanIndexForward": False,
        "Limit": limit,
    }

    if next_token:
        try:
            kwargs["ExclusiveStartKey"] = json.loads(
                base64.b64decode(next_token).decode()
            )
        except Exception:
            pass

    result = _get_table().query(**kwargs)
    items = [
        {
            "eventType": item.get("eventType", ""),
            "userId": item.get("userId", ""),
            "timestamp": item.get("timestamp", ""),
            "details": item.get("details", {}),
        }
        for item in result.get("Items", [])
    ]

    nt = None
    if result.get("LastEvaluatedKey"):
        nt = base64.b64encode(
            json.dumps(result["LastEvaluatedKey"]).encode()
        ).decode()

    return {"items": items, "nextToken": nt}


def get_metrics(days: int = 7) -> dict:
    """Aggregate metrics across recent audit logs."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    metrics = {
        "totalAiCalls": 0,
        "totalRagQueries": 0,
        "totalUserActions": 0,
        "activeUsers": set(),
        "aiCallsByProvider": {},
        "aiCallsByTask": {},
        "estimatedCost": Decimal("0"),
    }

    for i in range(days):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        result = _get_table().query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": f"AUDIT#{date}"},
        )
        for item in result.get("Items", []):
            event_type = item.get("eventType", "")
            user_id = item.get("userId", "")
            details = item.get("details", {})

            if user_id:
                metrics["activeUsers"].add(user_id)

            if event_type == "ai_call":
                metrics["totalAiCalls"] += 1
                provider = details.get("provider", "unknown")
                task = details.get("taskType", "unknown")
                metrics["aiCallsByProvider"][provider] = metrics["aiCallsByProvider"].get(provider, 0) + 1
                metrics["aiCallsByTask"][task] = metrics["aiCallsByTask"].get(task, 0) + 1
                cost = details.get("costEstimate", 0)
                if cost:
                    metrics["estimatedCost"] += Decimal(str(cost))

            elif event_type == "rag_query":
                metrics["totalRagQueries"] += 1

            elif event_type == "user_action":
                metrics["totalUserActions"] += 1

    metrics["activeUsers"] = len(metrics["activeUsers"])
    metrics["estimatedCost"] = float(metrics["estimatedCost"])
    return metrics


def _sanitize(d: dict) -> dict:
    """Convert floats to Decimal for DynamoDB compatibility."""
    out = {}
    for k, v in d.items():
        if isinstance(v, float):
            out[k] = Decimal(str(v))
        elif isinstance(v, dict):
            out[k] = _sanitize(v)
        else:
            out[k] = v
    return out
