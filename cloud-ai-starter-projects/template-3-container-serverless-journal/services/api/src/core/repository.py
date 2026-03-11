"""
DynamoDB repository — pure data access, no web framework dependencies.
Used by both the FastAPI adapter and the Lambda adapter.
"""

import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import time

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

TABLE_NAME = os.getenv("JOURNAL_TABLE_NAME", "journal")
DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT", "")


# Fast-fail config so our own retry loops react quickly (no internal boto3 retries).
_BOTO_CONFIG = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 1})


def _resource():
    kwargs: Dict[str, Any] = {
        "region_name": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        "config": _BOTO_CONFIG,
    }
    if DYNAMODB_ENDPOINT:
        kwargs["endpoint_url"] = DYNAMODB_ENDPOINT
    return boto3.resource("dynamodb", **kwargs)


def _table():
    return _resource().Table(TABLE_NAME)


# ── Key helpers ───────────────────────────────────────────────────────────────

def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def entry_sk(created_at: str, entry_id: str) -> str:
    return f"ENTRY#{created_at}#{entry_id}"


def lookup_sk(entry_id: str) -> str:
    return f"ENTRYID#{entry_id}"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def to_entry(item: Dict[str, Any]) -> Dict[str, Any]:
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
        "tags": list(item.get("tags", [])),
        "aiUpdatedAt": item.get("aiUpdatedAt"),
        "aiError": item.get("aiError"),
    }


# ── Local dev: auto-create table ──────────────────────────────────────────────

def ensure_table(retries: int = 12, delay: float = 3.0) -> None:
    """Create the DynamoDB table if missing. Only called in local mode.

    Uses ``create_table`` directly and catches ``ResourceInUseException`` when
    the table already exists — this avoids a ``DescribeTable`` round-trip that
    can time out while DynamoDB Local is still warming up.  The outer retry
    loop handles the case where the TCP port is open but the API isn't
    ready yet.
    """
    for attempt in range(1, retries + 1):
        try:
            ddb = _resource()
            ddb.create_table(
                TableName=TABLE_NAME,
                AttributeDefinitions=[
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                ],
                KeySchema=[
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            # DynamoDB Local creates tables synchronously — no need to wait.
            logger.info("DynamoDB table '%s' created.", TABLE_NAME)
            return
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "ResourceInUseException":
                logger.info("DynamoDB table '%s' already exists.", TABLE_NAME)
                return
            # Unexpected DynamoDB error — propagate immediately.
            raise
        except BotoCoreError as exc:
            logger.warning(
                "DynamoDB not ready for ensure_table (%d/%d): %s",
                attempt, retries, exc,
            )
            if attempt < retries:
                time.sleep(delay)

    logger.error("Could not ensure DynamoDB table after %d attempts — continuing.", retries)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_entry(user_id: str, title: str, body: str) -> Dict[str, Any]:
    table = _table()
    entry_id = str(uuid.uuid4())
    ts = now_iso()

    item: Dict[str, Any] = {
        "PK": user_pk(user_id),
        "SK": entry_sk(ts, entry_id),
        "entityType": "JOURNAL_ENTRY",
        "entryId": entry_id,
        "userId": user_id,
        "title": title,
        "body": body,
        "createdAt": ts,
        "updatedAt": ts,
        "aiStatus": "NOT_REQUESTED",
        "tags": [],
    }
    lookup: Dict[str, Any] = {
        "PK": user_pk(user_id),
        "SK": lookup_sk(entry_id),
        "entityType": "ENTRY_LOOKUP",
        "entryId": entry_id,
        "entrySk": item["SK"],
        "createdAt": ts,
    }
    table.put_item(Item=item)
    table.put_item(Item=lookup)
    return item


def resolve_entry(user_id: str, entry_id: str) -> Optional[Dict[str, Any]]:
    table = _table()
    lookup = table.get_item(
        Key={"PK": user_pk(user_id), "SK": lookup_sk(entry_id)}
    ).get("Item")
    if not lookup:
        return None
    item = table.get_item(
        Key={"PK": user_pk(user_id), "SK": lookup["entrySk"]}
    ).get("Item")
    return item if item and not item.get("deletedAt") else None


def list_entries(
    user_id: str, limit: int, next_token: Optional[str]
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    table = _table()
    params: Dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(user_pk(user_id))
        & Key("SK").begins_with("ENTRY#"),
        "Limit": limit,
        "ScanIndexForward": False,
    }
    if next_token:
        try:
            params["ExclusiveStartKey"] = json.loads(
                base64.urlsafe_b64decode(next_token.encode()).decode()
            )
        except Exception as exc:
            raise ValueError("invalid nextToken") from exc

    result = table.query(**params)
    items = [to_entry(i) for i in result.get("Items", []) if not i.get("deletedAt")]
    encoded: Optional[str] = None
    if result.get("LastEvaluatedKey"):
        encoded = base64.urlsafe_b64encode(
            json.dumps(result["LastEvaluatedKey"]).encode()
        ).decode()
    return items, encoded


def update_entry(
    user_id: str,
    entry_id: str,
    title: Optional[str],
    body: Optional[str],
) -> Optional[Dict[str, Any]]:
    table = _table()
    item = resolve_entry(user_id, entry_id)
    if not item:
        return None

    parts = ["updatedAt = :u"]
    names: Dict[str, str] = {}
    values: Dict[str, Any] = {":u": now_iso()}

    if title is not None:
        names["#title"] = "title"
        values[":title"] = title
        parts.append("#title = :title")
    if body is not None:
        names["#body"] = "body"
        values[":body"] = body
        parts.append("#body = :body")

    args: Dict[str, Any] = {
        "Key": {"PK": item["PK"], "SK": item["SK"]},
        "UpdateExpression": "SET " + ", ".join(parts),
        "ExpressionAttributeValues": values,
        "ReturnValues": "ALL_NEW",
    }
    if names:
        args["ExpressionAttributeNames"] = names
    return table.update_item(**args)["Attributes"]


def soft_delete_entry(user_id: str, entry_id: str) -> bool:
    table = _table()
    item = resolve_entry(user_id, entry_id)
    if not item:
        return False
    ts = now_iso()
    table.update_item(
        Key={"PK": item["PK"], "SK": item["SK"]},
        UpdateExpression="SET deletedAt = :d, updatedAt = :u",
        ExpressionAttributeValues={":d": ts, ":u": ts},
    )
    return True
