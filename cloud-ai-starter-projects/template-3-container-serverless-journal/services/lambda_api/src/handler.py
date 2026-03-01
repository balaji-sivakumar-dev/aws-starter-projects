import base64
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from boto3.dynamodb.conditions import Key

TABLE = boto3.resource("dynamodb").Table(os.environ["JOURNAL_TABLE_NAME"])
SFN = boto3.client("stepfunctions")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
        "body": json.dumps(body),
    }


def error(err: ApiError, request_id: str):
    return response(err.status, {"code": err.code, "message": err.message, "requestId": request_id})


def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def entry_sk(created_at: str, entry_id: str) -> str:
    return f"ENTRY#{created_at}#{entry_id}"


def lookup_sk(entry_id: str) -> str:
    return f"ENTRYID#{entry_id}"


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
        "tags": item.get("tags", []),
        "aiUpdatedAt": item.get("aiUpdatedAt"),
        "aiError": item.get("aiError"),
    }


def get_user_id(event: Dict[str, Any]) -> str:
    claims = (((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt") or {}).get("claims") or {}
    user_id = str(claims.get("sub") or "")
    if not user_id:
        raise ApiError(401, "UNAUTHORIZED", "missing valid token")
    return user_id


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    raw = event.get("body") or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError(400, "VALIDATION_ERROR", "invalid JSON body") from exc
    if not isinstance(data, dict):
        raise ApiError(400, "VALIDATION_ERROR", "JSON body must be an object")
    return data


def create_entry(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    body = str(payload.get("body") or "").strip()
    if not title:
        raise ApiError(400, "VALIDATION_ERROR", "title is required")
    if not body:
        raise ApiError(400, "VALIDATION_ERROR", "body is required")

    entry_id = str(uuid.uuid4())
    ts = now_iso()

    item = {
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

    lookup = {
        "PK": user_pk(user_id),
        "SK": lookup_sk(entry_id),
        "entityType": "ENTRY_LOOKUP",
        "entryId": entry_id,
        "entrySk": item["SK"],
        "createdAt": ts,
    }

    TABLE.put_item(Item=item, ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)")
    TABLE.put_item(Item=lookup, ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)")
    return item


def resolve_entry(user_id: str, entry_id: str) -> Dict[str, Any]:
    lookup = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": lookup_sk(entry_id)}).get("Item")
    if not lookup:
        raise ApiError(404, "NOT_FOUND", "entry not found")
    item = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": lookup["entrySk"]}).get("Item")
    if not item or item.get("deletedAt"):
        raise ApiError(404, "NOT_FOUND", "entry not found")
    return item


def list_entries(user_id: str, limit: int, next_token: Optional[str]):
    params: Dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("ENTRY#"),
        "Limit": limit,
        "ScanIndexForward": False,
    }
    if next_token:
        try:
            params["ExclusiveStartKey"] = json.loads(base64.urlsafe_b64decode(next_token).decode("utf-8"))
        except Exception as exc:
            raise ApiError(400, "VALIDATION_ERROR", "invalid nextToken") from exc

    result = TABLE.query(**params)
    items = [to_entry(i) for i in result.get("Items", []) if not i.get("deletedAt")]
    encoded = None
    if result.get("LastEvaluatedKey"):
        encoded = base64.urlsafe_b64encode(json.dumps(result["LastEvaluatedKey"]).encode("utf-8")).decode("utf-8")
    return items, encoded


def handler(event, context):
    request_id = ((event.get("requestContext") or {}).get("requestId") or getattr(context, "aws_request_id", "unknown-request-id"))

    try:
        method = str((((event.get("requestContext") or {}).get("http") or {}).get("method") or "GET")).upper()
        path = str((((event.get("requestContext") or {}).get("http") or {}).get("path") or "/")).rstrip("/") or "/"

        if method == "GET" and path == "/health":
            return response(200, {"status": "ok", "requestId": request_id})

        user_id = get_user_id(event)

        if method == "GET" and path == "/me":
            return response(200, {"userId": user_id, "requestId": request_id})

        if method == "GET" and path == "/entries":
            query = event.get("queryStringParameters") or {}
            limit = int(query.get("limit") or 20)
            limit = max(1, min(limit, 100))
            items, next_token = list_entries(user_id, limit, query.get("nextToken"))
            return response(200, {"items": items, "nextToken": next_token, "requestId": request_id})

        if method == "POST" and path == "/entries":
            item = create_entry(user_id, parse_body(event))
            return response(201, {"item": to_entry(item), "requestId": request_id})

        path_params = event.get("pathParameters") or {}
        entry_id = str(path_params.get("entryId") or "").strip()
        if not entry_id:
            raise ApiError(400, "VALIDATION_ERROR", "entryId is required")

        if method == "GET" and path == f"/entries/{entry_id}":
            item = resolve_entry(user_id, entry_id)
            return response(200, {"item": to_entry(item), "requestId": request_id})

        if method == "PUT" and path == f"/entries/{entry_id}":
            item = resolve_entry(user_id, entry_id)
            payload = parse_body(event)
            updates = ["updatedAt = :u"]
            names: Dict[str, str] = {}
            values: Dict[str, Any] = {":u": now_iso()}
            if "title" in payload:
                title = str(payload.get("title") or "").strip()
                if not title:
                    raise ApiError(400, "VALIDATION_ERROR", "title cannot be empty")
                names["#title"] = "title"
                values[":title"] = title
                updates.append("#title = :title")
            if "body" in payload:
                body = str(payload.get("body") or "").strip()
                if not body:
                    raise ApiError(400, "VALIDATION_ERROR", "body cannot be empty")
                names["#body"] = "body"
                values[":body"] = body
                updates.append("#body = :body")
            if len(updates) == 1:
                raise ApiError(400, "VALIDATION_ERROR", "nothing to update")

            args = {
                "Key": {"PK": item["PK"], "SK": item["SK"]},
                "UpdateExpression": "SET " + ", ".join(updates),
                "ExpressionAttributeValues": values,
                "ReturnValues": "ALL_NEW",
            }
            if names:
                args["ExpressionAttributeNames"] = names
            updated = TABLE.update_item(**args)["Attributes"]
            return response(200, {"item": to_entry(updated), "requestId": request_id})

        if method == "DELETE" and path == f"/entries/{entry_id}":
            item = resolve_entry(user_id, entry_id)
            TABLE.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET deletedAt = :d, updatedAt = :u",
                ExpressionAttributeValues={":d": now_iso(), ":u": now_iso()},
            )
            return response(200, {"deleted": True, "requestId": request_id})

        if method == "POST" and path == f"/entries/{entry_id}/ai":
            item = resolve_entry(user_id, entry_id)
            TABLE.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET aiStatus = :s, aiError = :e, updatedAt = :u",
                ExpressionAttributeValues={":s": "QUEUED", ":e": None, ":u": now_iso()},
            )
            exec_resp = SFN.start_execution(
                stateMachineArn=os.environ["WORKFLOW_ARN"],
                input=json.dumps({"userId": user_id, "entryId": entry_id, "requestId": request_id}),
            )
            return response(202, {"entryId": entry_id, "aiStatus": "QUEUED", "executionArn": exec_resp["executionArn"], "requestId": request_id})

        raise ApiError(404, "NOT_FOUND", "route not found")

    except ApiError as err:
        return error(err, request_id)
    except Exception:
        return error(ApiError(500, "INTERNAL_ERROR", "internal server error"), request_id)
