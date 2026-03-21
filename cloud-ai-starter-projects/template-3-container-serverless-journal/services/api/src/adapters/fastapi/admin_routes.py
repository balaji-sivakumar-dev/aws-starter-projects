"""Admin endpoints — usage metrics, audit logs, user activity."""

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from .deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Admin user IDs — comma-separated list in env var.
# In local mode, all users are admins.
ADMIN_USER_IDS = set(
    uid.strip()
    for uid in os.getenv("ADMIN_USER_IDS", "").split(",")
    if uid.strip()
)


def _require_admin(user_id: str) -> None:
    """Check if the current user is an admin."""
    app_env = os.getenv("APP_ENV", "local")
    if app_env in ("local", "test"):
        return  # everyone is admin in local/test mode
    if user_id not in ADMIN_USER_IDS:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "admin access required"},
        )


@router.get("/metrics")
async def get_metrics(
    days: int = Query(default=7, ge=1, le=90),
    user_id: str = Depends(get_current_user),
):
    """Get aggregate usage metrics (AI calls, RAG queries, active users)."""
    _require_admin(user_id)
    from ...core.audit import get_metrics
    return get_metrics(days=days)


@router.get("/audit")
async def get_audit_logs(
    date: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
    next_token: str = Query(default="", alias="nextToken"),
    user_id: str = Depends(get_current_user),
):
    """Get paginated audit logs for a specific date."""
    _require_admin(user_id)
    from ...core.audit import get_audit_logs

    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    result = get_audit_logs(date=date, limit=limit, next_token=next_token or None)
    return result


@router.get("/users")
async def list_users(
    user_id: str = Depends(get_current_user),
):
    """List all users who have created entries (scans DynamoDB for distinct USER# prefixes)."""
    _require_admin(user_id)
    from ...core.repository import _table

    table = _table()
    users = set()
    scan_kwargs = {
        "ProjectionExpression": "PK",
        "FilterExpression": "begins_with(PK, :prefix)",
        "ExpressionAttributeValues": {":prefix": "USER#"},
    }

    while True:
        result = table.scan(**scan_kwargs)
        for item in result.get("Items", []):
            pk = item.get("PK", "")
            if pk.startswith("USER#"):
                users.add(pk.removeprefix("USER#"))
        if "LastEvaluatedKey" not in result:
            break
        scan_kwargs["ExclusiveStartKey"] = result["LastEvaluatedKey"]

    return {
        "users": sorted(users),
        "totalUsers": len(users),
    }


@router.get("/users/{target_user_id}/activity")
async def get_user_activity(
    target_user_id: str,
    days: int = Query(default=7, ge=1, le=30),
    user_id: str = Depends(get_current_user),
):
    """Get recent activity for a specific user from audit logs."""
    _require_admin(user_id)
    from datetime import timedelta
    from ...core.audit import get_audit_logs

    now = datetime.now(timezone.utc)
    activity = []

    for i in range(days):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        result = get_audit_logs(date=date, limit=200)
        for item in result["items"]:
            if item.get("userId") == target_user_id:
                activity.append(item)

    return {
        "userId": target_user_id,
        "days": days,
        "totalEvents": len(activity),
        "events": activity[:100],  # cap at 100 most recent
    }


@router.get("/rag/status")
async def admin_rag_status(user_id: str = Depends(get_current_user)):
    """Get RAG embedding status across all users."""
    _require_admin(user_id)

    try:
        from ...rag.store_factory import get_vector_store
        store = get_vector_store()

        # Get users first, then count vectors per user
        from ...core.repository import _table
        table = _table()
        users = set()
        scan_kwargs = {
            "ProjectionExpression": "PK",
            "FilterExpression": "begins_with(PK, :prefix)",
            "ExpressionAttributeValues": {":prefix": "USER#"},
        }
        while True:
            result = table.scan(**scan_kwargs)
            for item in result.get("Items", []):
                pk = item.get("PK", "")
                if pk.startswith("USER#"):
                    users.add(pk.removeprefix("USER#"))
            if "LastEvaluatedKey" not in result:
                break
            scan_kwargs["ExclusiveStartKey"] = result["LastEvaluatedKey"]

        user_stats = []
        total_vectors = 0
        for uid in sorted(users):
            try:
                count = store.count(uid)
                total_vectors += count
                user_stats.append({"userId": uid, "vectors": count})
            except Exception:
                user_stats.append({"userId": uid, "vectors": 0, "error": "store unavailable"})

        return {
            "totalUsers": len(users),
            "totalVectors": total_vectors,
            "users": user_stats,
        }
    except ValueError:
        return {
            "totalUsers": 0,
            "totalVectors": 0,
            "users": [],
            "note": "VECTOR_STORE not configured",
        }
