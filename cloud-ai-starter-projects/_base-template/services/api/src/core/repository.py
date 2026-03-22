"""
DynamoDB repository — pure data access, no web framework dependencies.
Used by both the FastAPI adapter and the Lambda adapter.

Entity prefix: ITEM (replace with your domain entity, e.g., TXN, TASK, NOTE).
Table name: read from TABLE_NAME env var (set by config.sh / docker-compose).
"""

import base64
import json
import logging
import os
import time
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

TABLE_NAME = os.getenv("TABLE_NAME", "{{APP_PREFIX}}")
DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT", "")

# Fast-fail config so our own retry loops react quickly.
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
# Change the entity prefix (ITEM#, ITEMID#) to match your domain model.

def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def item_sk(created_at: str, item_id: str) -> str:
    return f"ITEM#{created_at}#{item_id}"


def lookup_sk(item_id: str) -> str:
    return f"ITEMID#{item_id}"


def summary_sk(summary_id: str) -> str:
    return f"SUMMARY#{summary_id}"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def to_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a DynamoDB record to the API response shape."""
    return {
        "itemId": raw["itemId"],
        "userId": raw["userId"],
        "title": raw["title"],
        "body": raw["body"],
        "data": raw.get("data", {}),
        "createdAt": raw["createdAt"],
        "updatedAt": raw["updatedAt"],
        "deletedAt": raw.get("deletedAt"),
        "aiStatus": raw.get("aiStatus", "NOT_REQUESTED"),
        "summary": raw.get("summary"),
        "tags": list(raw.get("tags", [])),
        "aiUpdatedAt": raw.get("aiUpdatedAt"),
        "aiError": raw.get("aiError"),
    }


def to_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "summaryId": raw["summaryId"],
        "userId": raw["userId"],
        "period": raw["period"],
        "periodLabel": raw["periodLabel"],
        "year": raw["year"],
        "week": raw.get("week"),
        "month": raw.get("month"),
        "startDate": raw["startDate"],
        "endDate": raw["endDate"],
        "entryCount": int(raw.get("entryCount", 0)),
        "narrative": raw.get("narrative", ""),
        "themes": list(raw.get("themes", [])),
        "mood": raw.get("mood", ""),
        "highlights": list(raw.get("highlights", [])),
        "reflection": raw.get("reflection", ""),
        "aiStatus": raw.get("aiStatus", "PROCESSING"),
        "aiError": raw.get("aiError"),
        "createdAt": raw["createdAt"],
        "updatedAt": raw["updatedAt"],
    }


# ── Local dev: auto-create table ──────────────────────────────────────────────

def ensure_table(retries: int = 12, delay: float = 3.0) -> None:
    """Create the DynamoDB table if missing. Only called in local mode."""
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
            logger.info("DynamoDB table '%s' created.", TABLE_NAME)
            return
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "ResourceInUseException":
                logger.info("DynamoDB table '%s' already exists.", TABLE_NAME)
                return
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

def create_item(user_id: str, title: str, body: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    table = _table()
    item_id = str(uuid.uuid4())
    ts = now_iso()

    item: Dict[str, Any] = {
        "PK": user_pk(user_id),
        "SK": item_sk(ts, item_id),
        "entityType": "ITEM",
        "itemId": item_id,
        "userId": user_id,
        "title": title,
        "body": body,
        "data": data or {},
        "createdAt": ts,
        "updatedAt": ts,
        "aiStatus": "NOT_REQUESTED",
        "tags": [],
    }
    lookup: Dict[str, Any] = {
        "PK": user_pk(user_id),
        "SK": lookup_sk(item_id),
        "entityType": "ITEM_LOOKUP",
        "itemId": item_id,
        "itemSk": item["SK"],
        "createdAt": ts,
    }
    table.put_item(Item=item)
    table.put_item(Item=lookup)
    return item


def resolve_item(user_id: str, item_id: str) -> Optional[Dict[str, Any]]:
    table = _table()
    lookup = table.get_item(
        Key={"PK": user_pk(user_id), "SK": lookup_sk(item_id)}
    ).get("Item")
    if not lookup:
        return None
    item = table.get_item(
        Key={"PK": user_pk(user_id), "SK": lookup["itemSk"]}
    ).get("Item")
    return item if item and not item.get("deletedAt") else None


def list_items(
    user_id: str, limit: int, next_token: Optional[str]
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    table = _table()
    params: Dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(user_pk(user_id))
        & Key("SK").begins_with("ITEM#"),
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
    items = [to_item(i) for i in result.get("Items", []) if not i.get("deletedAt")]
    encoded: Optional[str] = None
    if result.get("LastEvaluatedKey"):
        encoded = base64.urlsafe_b64encode(
            json.dumps(result["LastEvaluatedKey"]).encode()
        ).decode()
    return items, encoded


def update_item(
    user_id: str,
    item_id: str,
    title: Optional[str],
    body: Optional[str],
    data: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    table = _table()
    item = resolve_item(user_id, item_id)
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
    if data is not None:
        names["#data"] = "data"
        values[":data"] = data
        parts.append("#data = :data")

    args: Dict[str, Any] = {
        "Key": {"PK": item["PK"], "SK": item["SK"]},
        "UpdateExpression": "SET " + ", ".join(parts),
        "ExpressionAttributeValues": values,
        "ReturnValues": "ALL_NEW",
    }
    if names:
        args["ExpressionAttributeNames"] = names
    return table.update_item(**args)["Attributes"]


def count_items(user_id: str) -> int:
    """Return the count of non-deleted items for the user."""
    table = _table()
    total = 0
    params: Dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("ITEM#"),
        "FilterExpression": "attribute_not_exists(deletedAt)",
        "Select": "COUNT",
    }
    while True:
        result = table.query(**params)
        total += result.get("Count", 0)
        if not result.get("LastEvaluatedKey"):
            break
        params["ExclusiveStartKey"] = result["LastEvaluatedKey"]
    return total


def bulk_delete_items(user_id: str, item_ids: List[str]) -> int:
    """Soft-delete multiple items. Returns the number successfully deleted."""
    deleted = 0
    for iid in item_ids:
        if soft_delete_item(user_id, iid):
            deleted += 1
    return deleted


def soft_delete_item(user_id: str, item_id: str) -> bool:
    table = _table()
    item = resolve_item(user_id, item_id)
    if not item:
        return False
    ts = now_iso()
    table.update_item(
        Key={"PK": item["PK"], "SK": item["SK"]},
        UpdateExpression="SET deletedAt = :d, updatedAt = :u",
        ExpressionAttributeValues={":d": ts, ":u": ts},
    )
    return True


# ── Ask conversations ─────────────────────────────────────────────────────────

def conv_sk(created_at: str, conv_id: str) -> str:
    return f"CONV#{created_at}#{conv_id}"


def to_conversation(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "convId": item["convId"],
        "question": item["question"],
        "answer": item["answer"],
        "sources": item.get("sources", []),
        "createdAt": item["createdAt"],
    }


def _floats_to_decimal(obj: Any) -> Any:
    """Recursively convert float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, list):
        return [_floats_to_decimal(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _floats_to_decimal(v) for k, v in obj.items()}
    return obj


def create_conversation(
    user_id: str,
    question: str,
    answer: str,
    sources: List[Dict[str, Any]],
) -> Dict[str, Any]:
    table = _table()
    conv_id = str(uuid.uuid4())
    ts = now_iso()
    item: Dict[str, Any] = {
        "PK": user_pk(user_id),
        "SK": conv_sk(ts, conv_id),
        "entityType": "CONVERSATION",
        "convId": conv_id,
        "userId": user_id,
        "question": question,
        "answer": answer,
        "sources": _floats_to_decimal(sources),
        "createdAt": ts,
    }
    table.put_item(Item=item)
    return item


def list_conversations(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    result = _table().query(
        KeyConditionExpression=(
            Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("CONV#")
        ),
        ScanIndexForward=False,
        Limit=limit,
    )
    return [to_conversation(i) for i in result.get("Items", [])]


def delete_conversation(user_id: str, conv_id: str) -> bool:
    table = _table()
    result = table.query(
        KeyConditionExpression=(
            Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("CONV#")
        ),
    )
    for item in result.get("Items", []):
        if item.get("convId") == conv_id:
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
            return True
    return False


# ── Insights: items by date range ────────────────────────────────────────────

def get_items_in_range(
    user_id: str, start_date: str, end_date: str
) -> List[Dict[str, Any]]:
    """Return all non-deleted items whose createdAt falls within [start_date, end_date]."""
    table = _table()
    low = f"ITEM#{start_date}T00:00:00Z"
    high = f"ITEM#{end_date}T\xff"

    result = table.query(
        KeyConditionExpression=(
            Key("PK").eq(user_pk(user_id)) & Key("SK").between(low, high)
        ),
        ScanIndexForward=True,
    )
    return [
        to_item(i)
        for i in result.get("Items", [])
        if not i.get("deletedAt") and i.get("entityType") == "ITEM"
    ]


# ── Insights: period summaries CRUD ──────────────────────────────────────────

def create_summary(
    user_id: str,
    period: str,
    period_label: str,
    year: int,
    start_date: str,
    end_date: str,
    week: Optional[int] = None,
    month: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a PERIOD_SUMMARY placeholder (aiStatus=PROCESSING)."""
    table = _table()
    summary_id = str(uuid.uuid4())
    ts = now_iso()
    item: Dict[str, Any] = {
        "PK": user_pk(user_id),
        "SK": summary_sk(summary_id),
        "entityType": "PERIOD_SUMMARY",
        "summaryId": summary_id,
        "userId": user_id,
        "period": period,
        "periodLabel": period_label,
        "year": year,
        "startDate": start_date,
        "endDate": end_date,
        "entryCount": 0,
        "narrative": "",
        "themes": [],
        "mood": "",
        "highlights": [],
        "reflection": "",
        "aiStatus": "PROCESSING",
        "createdAt": ts,
        "updatedAt": ts,
    }
    if week is not None:
        item["week"] = week
    if month is not None:
        item["month"] = month
    table.put_item(Item=item)
    return item


def update_summary_result(
    user_id: str,
    summary_id: str,
    entry_count: int,
    narrative: str,
    themes: List[str],
    mood: str,
    highlights: List[str],
    reflection: str,
) -> None:
    _table().update_item(
        Key={"PK": user_pk(user_id), "SK": summary_sk(summary_id)},
        UpdateExpression=(
            "SET aiStatus = :s, entryCount = :ec, narrative = :n, "
            "themes = :th, mood = :mo, highlights = :hi, "
            "reflection = :rf, updatedAt = :u, aiError = :e"
        ),
        ExpressionAttributeValues={
            ":s": "DONE",
            ":ec": entry_count,
            ":n": narrative,
            ":th": themes,
            ":mo": mood,
            ":hi": highlights,
            ":rf": reflection,
            ":u": now_iso(),
            ":e": None,
        },
    )


def update_summary_error(user_id: str, summary_id: str, error: str) -> None:
    _table().update_item(
        Key={"PK": user_pk(user_id), "SK": summary_sk(summary_id)},
        UpdateExpression="SET aiStatus = :s, aiError = :e, updatedAt = :u",
        ExpressionAttributeValues={":s": "ERROR", ":e": error, ":u": now_iso()},
    )


def list_summaries(user_id: str) -> List[Dict[str, Any]]:
    result = _table().query(
        KeyConditionExpression=(
            Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("SUMMARY#")
        ),
        ScanIndexForward=False,
    )
    return [to_summary(i) for i in result.get("Items", [])]


def get_summary_item(user_id: str, summary_id: str) -> Optional[Dict[str, Any]]:
    result = _table().get_item(
        Key={"PK": user_pk(user_id), "SK": summary_sk(summary_id)}
    )
    item = result.get("Item")
    return item if item and item.get("entityType") == "PERIOD_SUMMARY" else None


def delete_summary(user_id: str, summary_id: str) -> bool:
    item = get_summary_item(user_id, summary_id)
    if not item:
        return False
    _table().delete_item(Key={"PK": user_pk(user_id), "SK": summary_sk(summary_id)})
    return True
