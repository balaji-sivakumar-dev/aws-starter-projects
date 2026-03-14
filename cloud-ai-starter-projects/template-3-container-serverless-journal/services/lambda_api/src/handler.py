import base64
import calendar
import datetime
import decimal
import json
import os
import traceback
import uuid
from typing import Any, Dict, Optional

import boto3
from boto3.dynamodb.conditions import Key

TABLE = boto3.resource("dynamodb").Table(os.environ["JOURNAL_TABLE_NAME"])
SFN = boto3.client("stepfunctions")

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class _Encoder(json.JSONEncoder):
    """Handle Decimal (DynamoDB returns all numbers as Decimal)."""
    def default(self, o: Any) -> Any:
        if isinstance(o, decimal.Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
        "body": json.dumps(body, cls=_Encoder),
    }


def error(err: ApiError, request_id: str):
    return response(err.status, {"code": err.code, "message": err.message, "requestId": request_id})


def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def entry_sk(created_at: str, entry_id: str) -> str:
    return f"ENTRY#{created_at}#{entry_id}"


def lookup_sk(entry_id: str) -> str:
    return f"ENTRYID#{entry_id}"


def summary_sk(summary_id: str) -> str:
    return f"SUMMARY#{summary_id}"


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


def to_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "summaryId": item["summaryId"],
        "userId": item["userId"],
        "period": item["period"],
        "year": item["year"],
        "month": item.get("month"),
        "week": item.get("week"),
        "periodLabel": item["periodLabel"],
        "startDate": item["startDate"],
        "endDate": item["endDate"],
        "entryCount": item.get("entryCount", 0),
        "aiStatus": item.get("aiStatus", "PENDING"),
        "mood": item.get("mood"),
        "narrative": item.get("narrative"),
        "themes": item.get("themes", []),
        "highlights": item.get("highlights", []),
        "reflection": item.get("reflection"),
        "aiError": item.get("aiError"),
        "createdAt": item.get("createdAt"),
        "updatedAt": item.get("updatedAt"),
    }


def get_user_id(event: Dict[str, Any]) -> str:
    claims = (((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt") or {}).get("claims") or {}
    user_id = str(claims.get("sub") or "")
    if not user_id:
        raise ApiError(401, "UNAUTHORIZED", "missing valid token")
    return user_id


def get_claims(event: Dict[str, Any]) -> Dict[str, Any]:
    return (((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt") or {}).get("claims") or {}


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    raw = event.get("body") or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError(400, "VALIDATION_ERROR", "invalid JSON body") from exc
    if not isinstance(data, dict):
        raise ApiError(400, "VALIDATION_ERROR", "JSON body must be an object")
    return data


def period_label(period: str, year: int, month: Optional[int], week: Optional[int]) -> str:
    if period == "monthly":
        return f"{MONTH_NAMES[month - 1]} {year}"
    if period == "weekly":
        return f"Week {week}, {year}"
    return str(year)


def period_dates(period: str, year: int, month: Optional[int], week: Optional[int]):
    if period == "monthly":
        _, last = calendar.monthrange(year, month)
        return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"
    if period == "weekly":
        jan4 = datetime.date(year, 1, 4)
        start = jan4 - datetime.timedelta(days=jan4.weekday()) + datetime.timedelta(weeks=week - 1)
        end = start + datetime.timedelta(days=6)
        return start.isoformat(), end.isoformat()
    return f"{year}-01-01", f"{year}-12-31"


def count_entries_in_range(user_id: str, start_date: str, end_date: str) -> int:
    result = TABLE.query(
        KeyConditionExpression=Key("PK").eq(user_pk(user_id))
        & Key("SK").between(f"ENTRY#{start_date}", f"ENTRY#{end_date}T99"),
    )
    return sum(1 for item in result.get("Items", []) if not item.get("deletedAt"))


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


def get_summary_item(user_id: str, summary_id: str) -> Dict[str, Any]:
    item = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": summary_sk(summary_id)}).get("Item")
    if not item:
        raise ApiError(404, "NOT_FOUND", "summary not found")
    return item


def handler(event, context):
    request_id = ((event.get("requestContext") or {}).get("requestId") or getattr(context, "aws_request_id", "unknown-request-id"))

    try:
        method = str((((event.get("requestContext") or {}).get("http") or {}).get("method") or "GET")).upper()
        path = str((((event.get("requestContext") or {}).get("http") or {}).get("path") or "/")).rstrip("/") or "/"
        path_params = event.get("pathParameters") or {}

        if method == "GET" and path == "/health":
            return response(200, {"status": "ok", "requestId": request_id})

        user_id = get_user_id(event)
        claims = get_claims(event)

        # ── /me ────────────────────────────────────────────────────────────────
        if method == "GET" and path == "/me":
            email = str(claims.get("email") or "")
            username = str(claims.get("cognito:username") or "")
            return response(200, {
                "userId": user_id,
                "email": email,
                "username": username,
                "requestId": request_id,
            })

        # ── Entries ────────────────────────────────────────────────────────────
        if method == "GET" and path == "/entries":
            query = event.get("queryStringParameters") or {}
            limit = int(query.get("limit") or 20)
            limit = max(1, min(limit, 100))
            items, next_token = list_entries(user_id, limit, query.get("nextToken"))
            return response(200, {"items": items, "nextToken": next_token, "requestId": request_id})

        if method == "POST" and path == "/entries":
            item = create_entry(user_id, parse_body(event))
            return response(201, {"item": to_entry(item), "requestId": request_id})

        entry_id = str(path_params.get("entryId") or "").strip()

        if method == "GET" and entry_id and path == f"/entries/{entry_id}":
            item = resolve_entry(user_id, entry_id)
            return response(200, {"item": to_entry(item), "requestId": request_id})

        if method == "PUT" and entry_id and path == f"/entries/{entry_id}":
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

        if method == "DELETE" and entry_id and path == f"/entries/{entry_id}":
            item = resolve_entry(user_id, entry_id)
            TABLE.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET deletedAt = :d, updatedAt = :u",
                ExpressionAttributeValues={":d": now_iso(), ":u": now_iso()},
            )
            return response(200, {"deleted": True, "requestId": request_id})

        if method == "POST" and entry_id and path == f"/entries/{entry_id}/ai":
            ai_enabled = os.environ.get("AI_ENABLED", "false").lower() == "true"
            if not ai_enabled:
                raise ApiError(503, "AI_NOT_CONFIGURED", "AI enrichment is not configured. Set AI_ENABLED=true and configure an LLM provider.")
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

        # ── Insights summaries ─────────────────────────────────────────────────
        if method == "GET" and path == "/insights/summaries":
            result = TABLE.query(
                KeyConditionExpression=Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("SUMMARY#"),
                ScanIndexForward=False,
            )
            items = [to_summary(i) for i in result.get("Items", [])]
            return response(200, {"items": items, "requestId": request_id})

        if method == "POST" and path == "/insights/summaries":
            payload = parse_body(event)
            period = str(payload.get("period") or "").strip()
            if period not in ("weekly", "monthly", "yearly"):
                raise ApiError(400, "VALIDATION_ERROR", "period must be weekly, monthly, or yearly")
            year = int(payload.get("year") or 0)
            if year < 2000 or year > 2100:
                raise ApiError(400, "VALIDATION_ERROR", "invalid year")
            month = int(payload.get("month") or 0) if period == "monthly" else None
            week = int(payload.get("week") or 0) if period == "weekly" else None
            if period == "monthly" and not (1 <= (month or 0) <= 12):
                raise ApiError(400, "VALIDATION_ERROR", "month must be 1-12")
            if period == "weekly" and not (1 <= (week or 0) <= 53):
                raise ApiError(400, "VALIDATION_ERROR", "week must be 1-53")

            label = period_label(period, year, month, week)
            start, end = period_dates(period, year, month, week)
            entry_count = count_entries_in_range(user_id, start, end)

            ai_enabled = os.environ.get("AI_ENABLED", "false").lower() == "true"
            initial_ai_status = "QUEUED" if ai_enabled else "NOT_CONFIGURED"

            summary_id = str(uuid.uuid4())
            ts = now_iso()
            item = {
                "PK": user_pk(user_id),
                "SK": summary_sk(summary_id),
                "entityType": "PERIOD_SUMMARY",
                "summaryId": summary_id,
                "userId": user_id,
                "period": period,
                "year": year,
                "periodLabel": label,
                "startDate": start,
                "endDate": end,
                "entryCount": entry_count,
                "aiStatus": initial_ai_status,
                "themes": [],
                "highlights": [],
                "createdAt": ts,
                "updatedAt": ts,
            }
            if month:
                item["month"] = month
            if week:
                item["week"] = week
            TABLE.put_item(Item=item)

            if ai_enabled:
                SFN.start_execution(
                    stateMachineArn=os.environ["WORKFLOW_ARN"],
                    input=json.dumps({
                        "type": "summary",
                        "userId": user_id,
                        "summaryId": summary_id,
                        "requestId": request_id,
                    }),
                )

            return response(201, {"item": to_summary(item), "requestId": request_id})

        summary_id = str(path_params.get("summaryId") or "").strip()

        if method == "GET" and summary_id and path == f"/insights/summaries/{summary_id}":
            item = get_summary_item(user_id, summary_id)
            return response(200, {"item": to_summary(item), "requestId": request_id})

        if method == "DELETE" and summary_id and path == f"/insights/summaries/{summary_id}":
            get_summary_item(user_id, summary_id)  # verify exists
            TABLE.delete_item(Key={"PK": user_pk(user_id), "SK": summary_sk(summary_id)})
            return response(200, {"deleted": True, "requestId": request_id})

        if method == "POST" and summary_id and path == f"/insights/summaries/{summary_id}/regenerate":
            ai_enabled = os.environ.get("AI_ENABLED", "false").lower() == "true"
            if not ai_enabled:
                raise ApiError(503, "AI_NOT_CONFIGURED", "AI enrichment is not configured. Set AI_ENABLED=true and configure an LLM provider.")
            item = get_summary_item(user_id, summary_id)
            TABLE.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET aiStatus = :s, aiError = :e, updatedAt = :u",
                ExpressionAttributeValues={":s": "QUEUED", ":e": None, ":u": now_iso()},
            )
            exec_resp = SFN.start_execution(
                stateMachineArn=os.environ["WORKFLOW_ARN"],
                input=json.dumps({
                    "type": "summary",
                    "userId": user_id,
                    "summaryId": summary_id,
                    "requestId": request_id,
                }),
            )
            updated = get_summary_item(user_id, summary_id)
            return response(202, {"item": to_summary(updated), "executionArn": exec_resp["executionArn"], "requestId": request_id})

        raise ApiError(404, "NOT_FOUND", "route not found")

    except ApiError as err:
        return error(err, request_id)
    except Exception:
        print(f"UNHANDLED ERROR requestId={request_id}\n{traceback.format_exc()}")
        return error(ApiError(500, "INTERNAL_ERROR", "internal server error"), request_id)
