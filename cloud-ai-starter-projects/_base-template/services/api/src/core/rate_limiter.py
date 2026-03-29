"""
Per-user daily rate limiter backed by DynamoDB.

Design:
  - Table key: PK=RATELIMIT#<user_id>  SK=<date>#<action>
  - Atomic ADD on `count` attribute.
  - TTL set to 48 h after midnight so records expire automatically.
  - Disabled entirely when APP_ENV is local or test.

Usage:
    from .rate_limiter import check_rate_limit

    check_rate_limit(user_id, "rag_ask")   # raises HTTPException 429 if over limit
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError
from fastapi import HTTPException

logger = logging.getLogger(__name__)

TABLE_NAME = os.getenv("TABLE_NAME", "{{APP_PREFIX}}")
APP_ENV = os.getenv("APP_ENV", "local")

# Default limits per action per user per UTC day.
# Override per-action via env vars:  RATE_LIMIT_RAG_ASK, RATE_LIMIT_EMBED_ALL, RATE_LIMIT_INSIGHTS
_DEFAULTS: dict[str, int] = {
    "rag_ask": 20,
    "embed_all": 5,
    "insights_generate": 10,
}


def _limit_for(action: str) -> int:
    env_key = f"RATE_LIMIT_{action.upper()}"
    raw = os.getenv(env_key, "")
    try:
        return int(raw) if raw else _DEFAULTS.get(action, 20)
    except ValueError:
        return _DEFAULTS.get(action, 20)


def _table():
    import boto3
    from botocore.config import Config

    kwargs: dict = {
        "region_name": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        "config": Config(connect_timeout=3, read_timeout=5, retries={"max_attempts": 1}),
    }
    endpoint = os.getenv("DYNAMODB_ENDPOINT", "")
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.resource("dynamodb", **kwargs).Table(TABLE_NAME)


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ttl_epoch() -> int:
    """TTL = end of tomorrow UTC (48 h after midnight)."""
    tomorrow = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=2)
    return int(tomorrow.timestamp())


def check_rate_limit(user_id: str, action: str) -> None:
    """
    Increment the daily call counter for (user_id, action).
    Raises HTTP 429 if the limit is exceeded.
    Does nothing when APP_ENV is 'local' or 'test'.
    """
    if APP_ENV in ("local", "test"):
        return

    limit = _limit_for(action)
    date = _today_utc()
    pk = f"RATELIMIT#{user_id}"
    sk = f"{date}#{action}"

    try:
        table = _table()
        response = table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression="ADD #count :one SET #ttl = if_not_exists(#ttl, :ttl)",
            ExpressionAttributeNames={"#count": "count", "#ttl": "ttl"},
            ExpressionAttributeValues={":one": 1, ":ttl": _ttl_epoch()},
            ReturnValues="UPDATED_NEW",
        )
        current = int(response["Attributes"].get("count", 1))
        logger.debug("Rate limit %s/%s for user %s: %d/%d", action, date, user_id, current, limit)

        if current > limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": (
                        f"Daily limit of {limit} calls for '{action}' reached. "
                        "Resets at midnight UTC."
                    ),
                    "limit": limit,
                    "used": current,
                    "resetsAt": f"{date}T23:59:59Z",
                },
            )
    except HTTPException:
        raise
    except ClientError as exc:
        # If DynamoDB is unavailable, log and allow the request through
        # (fail open — don't block users due to rate-limit infra issues).
        logger.warning("Rate limiter DynamoDB error for %s/%s: %s", user_id, action, exc)
    except Exception as exc:
        logger.warning("Rate limiter unexpected error: %s", exc)
