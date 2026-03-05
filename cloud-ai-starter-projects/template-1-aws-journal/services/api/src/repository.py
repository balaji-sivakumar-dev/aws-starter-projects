import base64
import json
import os
import uuid
from typing import Any, Dict, Optional, Tuple

import boto3
import logging
from botocore.exceptions import ClientError
from botocore.config import Config
from boto3.dynamodb.types import TypeSerializer
from boto3.dynamodb.conditions import Key

from errors import ApiError
from models import now_iso

_TABLE = None
_SERIALIZER = TypeSerializer()
logger = logging.getLogger(__name__)
_DDB_CLIENT = boto3.client("dynamodb", config=Config(parameter_validation=False))


def table():
    global _TABLE
    if _TABLE is None:
        _TABLE = boto3.resource("dynamodb").Table(os.environ["JOURNAL_TABLE_NAME"])
    return _TABLE


def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def entry_sk(created_at: str, entry_id: str) -> str:
    return f"ENTRY#{created_at}#{entry_id}"


def lookup_sk(entry_id: str) -> str:
    return f"ENTRYID#{entry_id}"


def encode_next_token(last_key: Dict[str, Any]) -> str:
    payload = json.dumps(last_key).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("utf-8")


def decode_next_token(next_token: str) -> Dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(next_token.encode("utf-8")).decode("utf-8")
        key = json.loads(raw)
        if not isinstance(key, dict):
            raise ValueError("decoded token is not object")
        return key
    except Exception as exc:  # noqa: BLE001
        raise ApiError(400, "VALIDATION_ERROR", "invalid nextToken") from exc


def create_entry(user_id: str, title: str, body: str) -> Dict[str, Any]:
    entry_id = str(uuid.uuid4())
    timestamp = now_iso()
    pk = user_pk(user_id)
    sk = entry_sk(timestamp, entry_id)

    entry_item = {
        "PK": pk,
        "SK": sk,
        "entityType": "JOURNAL_ENTRY",
        "entryId": entry_id,
        "userId": user_id,
        "title": title,
        "body": body,
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "aiStatus": "NOT_REQUESTED",
    }

    lookup_item = {
        "PK": pk,
        "SK": lookup_sk(entry_id),
        "entityType": "ENTRY_LOOKUP",
        "entryId": entry_id,
        "entrySk": sk,
        "createdAt": timestamp,
    }

    try:
        _DDB_CLIENT.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": table().name,
                        "Item": _marshal(entry_item),
                        "ConditionExpression": "attribute_not_exists(PK) AND attribute_not_exists(SK)",
                    }
                },
                {
                    "Put": {
                        "TableName": table().name,
                        "Item": _marshal(lookup_item),
                        "ConditionExpression": "attribute_not_exists(PK) AND attribute_not_exists(SK)",
                    }
                },
            ],
            ReturnCancellationReasons=True,
        )
    except ClientError as exc:
        reasons = exc.response.get("CancellationReasons")
        logger.error("TransactWriteItems failed reasons=%s", reasons)
        raise

    return entry_item


def list_entries(user_id: str, limit: int, next_token: Optional[str]) -> Tuple[list[Dict[str, Any]], Optional[str]]:
    params: Dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("ENTRY#"),
        "Limit": limit,
        "ScanIndexForward": False,
    }

    if next_token:
        params["ExclusiveStartKey"] = decode_next_token(next_token)

    result = table().query(**params)
    all_items = result.get("Items", [])
    items = [item for item in all_items if not item.get("deletedAt")]
    encoded = None
    if result.get("LastEvaluatedKey"):
        encoded = encode_next_token(result["LastEvaluatedKey"])
    return items, encoded


def get_entry(user_id: str, entry_id: str) -> Dict[str, Any]:
    item = _get_entry_for_user(user_id, entry_id)
    if item.get("deletedAt"):
        raise ApiError(404, "NOT_FOUND", "entry not found")
    return item


def update_entry(user_id: str, entry_id: str, updates: Dict[str, str]) -> Dict[str, Any]:
    item = _get_entry_for_user(user_id, entry_id)
    if item.get("deletedAt"):
        raise ApiError(404, "NOT_FOUND", "entry not found")

    expression_names = {"#updatedAt": "updatedAt"}
    expression_values = {":updatedAt": now_iso()}
    set_parts = ["#updatedAt = :updatedAt"]

    if "title" in updates:
        expression_names["#title"] = "title"
        expression_values[":title"] = updates["title"]
        set_parts.append("#title = :title")

    if "body" in updates:
        expression_names["#body"] = "body"
        expression_values[":body"] = updates["body"]
        set_parts.append("#body = :body")

    response = table().update_item(
        Key={"PK": item["PK"], "SK": item["SK"]},
        UpdateExpression="SET " + ", ".join(set_parts),
        ExpressionAttributeNames=expression_names,
        ExpressionAttributeValues=expression_values,
        ReturnValues="ALL_NEW",
    )
    return response["Attributes"]


def soft_delete_entry(user_id: str, entry_id: str) -> None:
    item = _get_entry_for_user(user_id, entry_id)
    if item.get("deletedAt"):
        return

    table().update_item(
        Key={"PK": item["PK"], "SK": item["SK"]},
        UpdateExpression="SET deletedAt = :deletedAt, updatedAt = :updatedAt",
        ExpressionAttributeValues={
            ":deletedAt": now_iso(),
            ":updatedAt": now_iso(),
        },
    )


def mark_ai_queued(user_id: str, entry_id: str) -> Dict[str, Any]:
    item = _get_entry_for_user(user_id, entry_id)
    if item.get("deletedAt"):
        raise ApiError(404, "NOT_FOUND", "entry not found")

    response = table().update_item(
        Key={"PK": item["PK"], "SK": item["SK"]},
        UpdateExpression="SET aiStatus = :status, aiError = :error, updatedAt = :updatedAt",
        ExpressionAttributeValues={
            ":status": "QUEUED",
            ":error": None,
            ":updatedAt": now_iso(),
        },
        ReturnValues="ALL_NEW",
    )
    return response["Attributes"]


def _get_entry_for_user(user_id: str, entry_id: str) -> Dict[str, Any]:
    lookup = table().get_item(Key={"PK": user_pk(user_id), "SK": lookup_sk(entry_id)}).get("Item")
    if not lookup:
        raise ApiError(404, "NOT_FOUND", "entry not found")

    entry = table().get_item(Key={"PK": user_pk(user_id), "SK": lookup["entrySk"]}).get("Item")
    if not entry:
        raise ApiError(404, "NOT_FOUND", "entry not found")
    return entry


def _marshal(item: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    return {key: _SERIALIZER.serialize(value) for key, value in item.items()}
