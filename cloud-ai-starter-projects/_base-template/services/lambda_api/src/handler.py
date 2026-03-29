import base64
import calendar
import datetime
import decimal
import json
import os
import traceback
import uuid
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key

from embeddings import embed_text
from llm_provider import ask as llm_ask, provider_name as llm_provider_name
from vector_store import count_vectors, delete_all_vectors, search_vectors, upsert_vector

_DDB = boto3.resource("dynamodb")
TABLE = _DDB.Table(os.environ["TABLE_NAME"])
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
        "entryDate": item.get("entryDate", item["createdAt"][:10]),  # YYYY-MM-DD, defaults to creation date
        "createdAt": item["createdAt"],
        "updatedAt": item["updatedAt"],
        "deletedAt": item.get("deletedAt"),
        "aiStatus": item.get("aiStatus", "NOT_REQUESTED"),
        "summary": item.get("summary"),
        "tags": item.get("tags", []),
        "aiUpdatedAt": item.get("aiUpdatedAt"),
        "aiError": item.get("aiError"),
        "aiProvider": item.get("aiProvider"),
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
        "aiProvider": item.get("aiProvider"),
    }


# ── Conversation key helpers ──────────────────────────────────────────────────

def conv_sk(ts: str, conv_id: str) -> str:
    return f"CONV#{ts}#{conv_id}"


def to_conversation(item: Dict[str, Any]) -> Dict[str, Any]:
    sources = item.get("sources", [])
    if isinstance(sources, str):
        try:
            sources = json.loads(sources)
        except Exception:
            sources = []
    return {
        "convId": item.get("convId", ""),
        "question": item.get("question", ""),
        "answer": item.get("answer", ""),
        "sources": sources,
        "provider": item.get("provider", ""),
        "createdAt": item.get("createdAt", ""),
    }


# ── Audit log helpers ─────────────────────────────────────────────────────────

AUDIT_PK = "AUDIT"


def write_audit(user_id: str, event_type: str, request_id: str, details: Optional[Dict] = None,
                email: str = "", username: str = "") -> None:
    """Write an audit log entry to DynamoDB. Never raises."""
    try:
        ts = now_iso()
        TABLE.put_item(Item={
            "PK": AUDIT_PK,
            "SK": f"LOG#{ts[:10]}#{ts}#{request_id}",
            "entityType": "AUDIT_LOG",
            "userId": user_id or "anonymous",
            "email": email or "",
            "username": username or "",
            "eventType": event_type,
            "requestId": request_id,
            "timestamp": ts,
            "details": details or {},
        })
    except Exception:
        pass  # audit failures must never break requests


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


def create_item(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    body = str(payload.get("body") or "").strip()
    if not title:
        raise ApiError(400, "VALIDATION_ERROR", "title is required")
    if not body:
        raise ApiError(400, "VALIDATION_ERROR", "body is required")

    item_id = str(uuid.uuid4())
    ts = now_iso()
    # entryDate: user-selected date (YYYY-MM-DD) — defaults to today
    raw_date = str(payload.get("entryDate") or "").strip()
    entry_date = raw_date if raw_date and len(raw_date) == 10 else ts[:10]

    item = {
        "PK": user_pk(user_id),
        "SK": entry_sk(ts, item_id),
        "entityType": "ITEM",
        "entryId": item_id,
        "userId": user_id,
        "title": title,
        "body": body,
        "entryDate": entry_date,
        "createdAt": ts,
        "updatedAt": ts,
        "aiStatus": "NOT_REQUESTED",
        "tags": [],
    }

    lookup = {
        "PK": user_pk(user_id),
        "SK": lookup_sk(item_id),
        "entityType": "ITEM_LOOKUP",
        "entryId": item_id,
        "entrySk": item["SK"],
        "createdAt": ts,
    }

    TABLE.put_item(Item=item, ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)")
    TABLE.put_item(Item=lookup, ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)")
    return item


def resolve_item(user_id: str, item_id: str) -> Dict[str, Any]:
    lookup = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": lookup_sk(item_id)}).get("Item")
    if not lookup:
        raise ApiError(404, "NOT_FOUND", "item not found")
    item = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": lookup["entrySk"]}).get("Item")
    if not item or item.get("deletedAt"):
        raise ApiError(404, "NOT_FOUND", "item not found")
    return item


def list_items(user_id: str, limit: int, next_token: Optional[str]):
    params: Dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("ENTRY#"),
        "Limit": limit,
        "ScanIndexForward": False,
        "ConsistentRead": True,  # avoid read-after-write misses on refresh
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


def embed_sk(entry_id: str) -> str:
    return f"VECTOR#{entry_id}"


def list_all_items(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all non-deleted items for the user (for bulk embed)."""
    result = TABLE.query(
        KeyConditionExpression=Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("ENTRY#"),
        ScanIndexForward=False,
    )
    return [i for i in result.get("Items", []) if not i.get("deletedAt")]


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

        # ── Public config (no auth required) ───────────────────────────────────
        if method == "GET" and path == "/config/providers":
            providers = []
            if os.environ.get("AI_ENABLED", "false").lower() == "true" or os.environ.get("BEDROCK_MODEL_ID"):
                providers.append({
                    "name": "bedrock",
                    "label": f"AWS Bedrock ({os.environ.get('BEDROCK_MODEL_ID', 'nova-lite')})",
                    "configured": True,
                })
            if os.environ.get("GROQ_API_KEY"):
                providers.append({
                    "name": "groq",
                    "label": f"Groq ({os.environ.get('GROQ_MODEL_ID', 'llama-3.1-8b-instant')})",
                    "configured": True,
                })
            if os.environ.get("OPENAI_API_KEY"):
                providers.append({
                    "name": "openai",
                    "label": f"OpenAI ({os.environ.get('OPENAI_LLM_MODEL', 'gpt-4o-mini')})",
                    "configured": True,
                })
            default_provider = os.environ.get("LLM_PROVIDER", "bedrock")
            return response(200, {
                "providers": providers,
                "default": default_provider,
                "requestId": request_id,
            })

        user_id = get_user_id(event)
        claims = get_claims(event)
        # Caller identity — stored in all audit log entries written from this request
        _email    = str(claims.get("email") or "").strip().lower()
        _username = str(claims.get("cognito:username") or claims.get("username") or "").strip()

        # ── /me ────────────────────────────────────────────────────────────────
        if method == "GET" and path == "/me":
            email = str(claims.get("email") or "").strip().lower()
            username = str(claims.get("cognito:username") or "")
            admin_emails = {
                e.strip().lower()
                for e in os.environ.get("ADMIN_EMAILS", "").split(",")
                if e.strip()
            }
            return response(200, {
                "userId": user_id,
                "email": email,
                "username": username,
                "isAdmin": email in admin_emails,
                "requestId": request_id,
            })

        # ── Entries ────────────────────────────────────────────────────────────
        if method == "GET" and path == "/entries":
            query = event.get("queryStringParameters") or {}
            limit = int(query.get("limit") or 50)
            limit = max(1, min(limit, 100))
            items, next_token = list_items(user_id, limit, query.get("nextToken"))
            return response(200, {"items": items, "nextToken": next_token, "requestId": request_id})

        if method == "GET" and path == "/entries/count":
            # Count all non-deleted entries for user (paginated DynamoDB query)
            total = 0
            last_key = None
            while True:
                params: Dict[str, Any] = {
                    "KeyConditionExpression": Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("ENTRY#"),
                    "Select": "ALL_ATTRIBUTES",
                    "ConsistentRead": True,
                }
                if last_key:
                    params["ExclusiveStartKey"] = last_key
                result = TABLE.query(**params)
                total += sum(1 for i in result.get("Items", []) if not i.get("deletedAt"))
                last_key = result.get("LastEvaluatedKey")
                if not last_key:
                    break
            return response(200, {"count": total, "requestId": request_id})

        if method == "POST" and path == "/entries/bulk-delete":
            payload = parse_body(event)
            item_ids = payload.get("itemIds", [])
            if not isinstance(item_ids, list) or len(item_ids) == 0:
                raise ApiError(400, "VALIDATION_ERROR", "itemIds must be a non-empty list")
            if len(item_ids) > 200:
                raise ApiError(400, "VALIDATION_ERROR", "cannot delete more than 200 items at once")
            deleted_count = 0
            ts = now_iso()
            for eid in item_ids:
                try:
                    lookup = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": lookup_sk(str(eid))}).get("Item")
                    if not lookup:
                        continue
                    item = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": lookup["entrySk"]}).get("Item")
                    if not item or item.get("deletedAt"):
                        continue
                    TABLE.update_item(
                        Key={"PK": item["PK"], "SK": item["SK"]},
                        UpdateExpression="SET deletedAt = :d, updatedAt = :u",
                        ExpressionAttributeValues={":d": ts, ":u": ts},
                    )
                    deleted_count += 1
                except Exception:
                    pass
            write_audit(user_id, "BULK_DELETE_ENTRIES", request_id, {"count": deleted_count}, email=_email, username=_username)
            return response(200, {"deleted": deleted_count, "requestId": request_id})

        if method == "POST" and path == "/entries/bulk-import":
            payload = parse_body(event)
            rows = payload.get("entries", [])
            if not isinstance(rows, list) or len(rows) == 0:
                raise ApiError(400, "VALIDATION_ERROR", "entries must be a non-empty list")
            if len(rows) > 500:
                raise ApiError(400, "VALIDATION_ERROR", "cannot import more than 500 entries at once")
            imported, failed, errors = 0, 0, []
            for row in rows:
                try:
                    title = str(row.get("title") or "").strip()
                    body = str(row.get("body") or "").strip()
                    if not title or not body:
                        raise ValueError("title and body are required")
                    item = create_item(user_id, {
                        "title": title,
                        "body": body,
                        "entryDate": str(row.get("entryDate") or row.get("date") or "").strip(),
                    })
                    imported += 1
                except Exception as exc:
                    failed += 1
                    errors.append({"title": str(row.get("title") or "")[:60], "error": str(exc)})
            write_audit(user_id, "BULK_IMPORT_ENTRIES", request_id, {"imported": imported, "failed": failed}, email=_email, username=_username)
            return response(201, {"imported": imported, "failed": failed, "errors": errors, "requestId": request_id})

        if method == "POST" and path == "/entries":
            item = create_item(user_id, parse_body(event))
            write_audit(user_id, "CREATE_ENTRY", request_id, {"entryId": item["entryId"]}, email=_email, username=_username)
            return response(201, {"item": to_entry(item), "requestId": request_id})

        entry_id = str(path_params.get("entryId") or "").strip()

        if method == "GET" and entry_id and path == f"/entries/{entry_id}":
            item = resolve_item(user_id, entry_id)
            return response(200, {"item": to_entry(item), "requestId": request_id})

        if method == "PUT" and entry_id and path == f"/entries/{entry_id}":
            item = resolve_item(user_id, entry_id)
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
            if "entryDate" in payload:
                raw_date = str(payload.get("entryDate") or "").strip()
                if raw_date and len(raw_date) == 10:
                    values[":entryDate"] = raw_date
                    updates.append("entryDate = :entryDate")
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
            write_audit(user_id, "UPDATE_ENTRY", request_id, {"entryId": entry_id}, email=_email, username=_username)
            return response(200, {"item": to_entry(updated), "requestId": request_id})

        if method == "DELETE" and entry_id and path == f"/entries/{entry_id}":
            item = resolve_item(user_id, entry_id)
            TABLE.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET deletedAt = :d, updatedAt = :u",
                ExpressionAttributeValues={":d": now_iso(), ":u": now_iso()},
            )
            write_audit(user_id, "DELETE_ENTRY", request_id, {"entryId": entry_id}, email=_email, username=_username)
            return response(200, {"deleted": True, "requestId": request_id})

        if method == "POST" and entry_id and path == f"/entries/{entry_id}/ai":
            ai_enabled = os.environ.get("AI_ENABLED", "false").lower() == "true"
            if not ai_enabled:
                raise ApiError(503, "AI_NOT_CONFIGURED", "AI enrichment is not configured. Set AI_ENABLED=true and configure an LLM provider.")
            item = resolve_item(user_id, entry_id)
            TABLE.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET aiStatus = :s, aiError = :e, updatedAt = :u",
                ExpressionAttributeValues={":s": "QUEUED", ":e": None, ":u": now_iso()},
            )
            headers = event.get("headers") or {}
            provider_req = headers.get("x-llm-provider", "").lower().strip()
            sfn_input: Dict[str, Any] = {"userId": user_id, "entryId": entry_id, "requestId": request_id}
            if provider_req in {"bedrock", "groq", "openai"}:
                sfn_input["providerOverride"] = provider_req
            exec_resp = SFN.start_execution(
                stateMachineArn=os.environ["WORKFLOW_ARN"],
                input=json.dumps(sfn_input),
            )
            write_audit(user_id, "TRIGGER_AI", request_id, {"entryId": entry_id}, email=_email, username=_username)
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
                headers = event.get("headers") or {}
                provider_req = headers.get("x-llm-provider", "").lower().strip()
                sfn_input_s: Dict[str, Any] = {"type": "summary", "userId": user_id, "summaryId": summary_id, "requestId": request_id}
                if provider_req in {"bedrock", "groq", "openai"}:
                    sfn_input_s["providerOverride"] = provider_req
                SFN.start_execution(
                    stateMachineArn=os.environ["WORKFLOW_ARN"],
                    input=json.dumps(sfn_input_s),
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
            headers = event.get("headers") or {}
            provider_req = headers.get("x-llm-provider", "").lower().strip()
            sfn_regen: Dict[str, Any] = {"type": "summary", "userId": user_id, "summaryId": summary_id, "requestId": request_id}
            if provider_req in {"bedrock", "groq", "openai"}:
                sfn_regen["providerOverride"] = provider_req
            exec_resp = SFN.start_execution(
                stateMachineArn=os.environ["WORKFLOW_ARN"],
                input=json.dumps(sfn_regen),
            )
            updated = get_summary_item(user_id, summary_id)
            return response(202, {"item": to_summary(updated), "executionArn": exec_resp["executionArn"], "requestId": request_id})

        # ── RAG ───────────────────────────────────────────────────────────────
        # All RAG routes require AI_ENABLED=true (Bedrock access via IAM).
        # Never exposed without JWT — API Gateway JWT authorizer enforced upstream.

        if method == "GET" and path == "/rag/status":
            embedded = count_vectors(user_id)
            total = len(list_all_items(user_id))
            return response(200, {
                "totalVectors": embedded,
                "totalEntries": total,
                "requestId": request_id,
            })

        if method == "POST" and path == "/rag/search":
            ai_enabled = os.environ.get("AI_ENABLED", "false").lower() == "true"
            if not ai_enabled:
                raise ApiError(503, "AI_NOT_CONFIGURED", "AI_ENABLED is not set to true.")
            payload = parse_body(event)
            query = str(payload.get("query") or "").strip()
            if not query:
                raise ApiError(400, "VALIDATION_ERROR", "query is required")
            top_k = min(int(payload.get("top_k") or payload.get("topK") or 5), 10)
            query_vec = embed_text(query)
            results = search_vectors(user_id, query_vec, top_k)
            write_audit(user_id, "RAG_SEARCH", request_id, {"query": query[:100]}, email=_email, username=_username)
            return response(200, {"results": results, "requestId": request_id})

        if method == "POST" and path == "/rag/ask":
            ai_enabled = os.environ.get("AI_ENABLED", "false").lower() == "true"
            if not ai_enabled:
                raise ApiError(503, "AI_NOT_CONFIGURED", "AI_ENABLED is not set to true.")
            payload = parse_body(event)
            question = str(payload.get("query") or payload.get("question") or "").strip()
            if not question:
                raise ApiError(400, "VALIDATION_ERROR", "query is required")

            # Per-request provider override via X-LLM-Provider header
            headers = event.get("headers") or {}
            requested_provider = headers.get("x-llm-provider", "").lower().strip()
            valid_providers = {"bedrock", "groq", "openai"}
            provider_override = requested_provider if requested_provider in valid_providers else None
            provider_name = llm_provider_name(provider_override)

            # Retrieve relevant context
            query_vec = embed_text(question)
            top_k = min(int(payload.get("top_k") or 5), 10)
            hits = search_vectors(user_id, query_vec, top_k=top_k)
            context_parts = [
                f"Entry: {h['title']}\n{h['bodySnippet']}" for h in hits
            ]
            context = "\n\n---\n\n".join(context_parts) if context_parts else "(no relevant entries found)"

            # Call LLM — use per-request provider override if supplied via header
            prompt = (
                "You are a helpful AI assistant. Answer the user's question "
                "based only on the items provided below. "
                "If the entries don't contain relevant information, say so.\n\n"
                f"Items:\n{context}\n\n"
                f"Question: {question}"
            )
            answer = llm_ask(prompt, max_tokens=1024, provider=provider_override)

            # Persist conversation to DynamoDB
            conv_id = str(uuid.uuid4())
            ts = now_iso()
            sources_data = [{"entryId": h["entryId"], "title": h["title"], "score": h["score"], "snippet": h.get("bodySnippet", ""), "createdAt": ""} for h in hits]
            try:
                TABLE.put_item(Item={
                    "PK": user_pk(user_id),
                    "SK": conv_sk(ts, conv_id),
                    "entityType": "CONVERSATION",
                    "convId": conv_id,
                    "question": question,
                    "answer": answer,
                    "sources": json.dumps(sources_data),
                    "provider": provider_name,
                    "createdAt": ts,
                })
            except Exception:
                pass  # conversation persistence failure must not break the response

            write_audit(user_id, "RAG_ASK", request_id, {"provider": provider_name, "query": question[:100]}, email=_email, username=_username)
            return response(200, {
                "answer": answer,
                "sources": sources_data,
                "provider": provider_name,
                "requestId": request_id,
            })

        if method == "GET" and path == "/rag/conversations":
            result = TABLE.query(
                KeyConditionExpression=Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("CONV#"),
                ScanIndexForward=False,
                Limit=50,
            )
            items = [to_conversation(i) for i in result.get("Items", [])]
            return response(200, {"items": items, "requestId": request_id})

        conv_id_param = str(path_params.get("convId") or "").strip()

        if method == "DELETE" and conv_id_param and path == f"/rag/conversations/{conv_id_param}":
            # Find by scanning for matching convId
            result = TABLE.query(
                KeyConditionExpression=Key("PK").eq(user_pk(user_id)) & Key("SK").begins_with("CONV#"),
            )
            deleted = False
            for item in result.get("Items", []):
                if item.get("convId") == conv_id_param:
                    TABLE.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                    deleted = True
                    break
            write_audit(user_id, "DELETE_CONVERSATION", request_id, {"convId": conv_id_param}, email=_email, username=_username)
            return response(200, {"deleted": deleted, "requestId": request_id})

        if method == "DELETE" and path == "/rag/vectors":
            count = delete_all_vectors(user_id)
            write_audit(user_id, "RAG_CLEAR_VECTORS", request_id, {"deleted": count}, email=_email, username=_username)
            return response(200, {"deleted": count, "requestId": request_id})

        if method == "POST" and path == "/rag/embed-all":
            ai_enabled = os.environ.get("AI_ENABLED", "false").lower() == "true"
            if not ai_enabled:
                raise ApiError(503, "AI_NOT_CONFIGURED", "AI_ENABLED is not set to true.")
            entries = list_all_items(user_id)
            embedded = 0
            failed = 0
            errors = []
            for entry in entries:
                try:
                    text = f"{entry.get('title', '')}\n\n{entry.get('body', '')}"
                    vector = embed_text(text)
                    upsert_vector(
                        user_id=user_id,
                        entry_id=entry["entryId"],
                        embedding=vector,
                        title=entry.get("title", ""),
                        body_snippet=entry.get("body", "")[:500],
                        updated_at=now_iso(),
                    )
                    embedded += 1
                except Exception as exc:
                    failed += 1
                    errors.append({
                        "entryId": entry.get("entryId", "unknown"),
                        "title": entry.get("title", "")[:60],
                        "error": str(exc),
                    })
            write_audit(user_id, "RAG_EMBED_ALL", request_id, {"embedded": embedded, "failed": failed, "total": len(entries)}, email=_email, username=_username)
            return response(200, {
                "embedded": embedded,
                "failed": failed,
                "totalEntries": len(entries),
                "errors": errors,
                "requestId": request_id,
            })

        # ── Admin routes ───────────────────────────────────────────────────────
        # All admin routes require the caller to be an admin (email in ADMIN_EMAILS).

        is_admin_path = path.startswith("/admin/")
        if is_admin_path:
            claims = get_claims(event)
            email = str(claims.get("email") or "").strip().lower()
            admin_emails = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
            if email not in admin_emails:
                raise ApiError(403, "FORBIDDEN", "admin access required")

        if method == "GET" and path == "/admin/audit":
            query = event.get("queryStringParameters") or {}
            date_filter = query.get("date", "")
            user_id_filter = query.get("userId", "").strip()
            limit = min(int(query.get("limit") or 200), 500)
            params: Dict[str, Any] = {
                "KeyConditionExpression": (
                    Key("PK").eq(AUDIT_PK) & Key("SK").begins_with(f"LOG#{date_filter}")
                    if date_filter else Key("PK").eq(AUDIT_PK)
                ),
                "ScanIndexForward": False,
                "Limit": limit,
            }
            result = TABLE.query(**params)
            items = []
            for item in result.get("Items", []):
                uid = item.get("userId", "")
                if user_id_filter and uid != user_id_filter:
                    continue
                items.append({
                    "eventType": item.get("eventType", ""),
                    "userId": uid,
                    "email": item.get("email", ""),
                    "username": item.get("username", ""),
                    "timestamp": item.get("timestamp", ""),
                    "requestId": item.get("requestId", ""),
                    "details": item.get("details", {}),
                })
            return response(200, {"items": items, "requestId": request_id})

        if method == "GET" and path == "/admin/metrics":
            query = event.get("queryStringParameters") or {}
            days = int(query.get("days") or 7)
            cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).date().isoformat()

            result = TABLE.query(
                KeyConditionExpression=Key("PK").eq(AUDIT_PK) & Key("SK").begins_with("LOG#"),
                FilterExpression="timestamp >= :cutoff",
                ExpressionAttributeValues={":cutoff": cutoff},
            )
            logs = result.get("Items", [])
            active_users: set = set()
            total_ai_calls = 0
            total_rag_queries = 0
            total_actions = len(logs)
            ai_calls_by_provider: Dict[str, int] = {}
            for log in logs:
                uid = log.get("userId", "")
                if uid and uid != "anonymous":
                    active_users.add(uid)
                event_type = log.get("eventType", "")
                if event_type in ("RAG_ASK",):
                    total_ai_calls += 1
                    p = (log.get("details") or {}).get("provider", "unknown")
                    ai_calls_by_provider[p] = ai_calls_by_provider.get(p, 0) + 1
                if event_type in ("RAG_ASK", "RAG_SEARCH"):
                    total_rag_queries += 1
            return response(200, {
                "activeUsers": len(active_users),
                "totalAiCalls": total_ai_calls,
                "totalRagQueries": total_rag_queries,
                "totalUserActions": total_actions,
                "aiCallsByProvider": ai_calls_by_provider,
                "estimatedCost": 0.0,
                "requestId": request_id,
            })

        if method == "GET" and path == "/admin/users":
            # Build a deduplicated user list from audit logs.
            # Each audit entry may carry email/username — take the most recent values per userId.
            result = TABLE.query(
                KeyConditionExpression=Key("PK").eq(AUDIT_PK),
                ScanIndexForward=False,
                Limit=2000,
            )
            user_map: Dict[str, Dict[str, str]] = {}  # userId → {email, username, lastSeen}
            for item in result.get("Items", []):
                uid = item.get("userId", "")
                if not uid or uid == "anonymous":
                    continue
                if uid not in user_map:
                    user_map[uid] = {
                        "userId": uid,
                        "email": item.get("email", ""),
                        "username": item.get("username", ""),
                        "lastSeen": item.get("timestamp", ""),
                    }
                else:
                    # Fill in missing email/username from older entries
                    if not user_map[uid]["email"] and item.get("email"):
                        user_map[uid]["email"] = item["email"]
                    if not user_map[uid]["username"] and item.get("username"):
                        user_map[uid]["username"] = item["username"]
            users = sorted(user_map.values(), key=lambda u: u.get("email") or u["userId"])
            return response(200, {"users": users, "totalUsers": len(users), "requestId": request_id})

        if method == "GET" and path == "/admin/rag/status":
            # Count all VECTOR# items across all users via scan (admin only)
            scan_result = TABLE.scan(
                FilterExpression="entityType = :e",
                ExpressionAttributeValues={":e": "ENTRY_VECTOR"},
                Select="COUNT",
            )
            total_vectors = scan_result.get("Count", 0)
            # Count distinct users with vectors
            scan_result2 = TABLE.scan(
                FilterExpression="entityType = :e",
                ExpressionAttributeValues={":e": "ENTRY_VECTOR"},
                ProjectionExpression="PK",
            )
            user_pks = {item["PK"] for item in scan_result2.get("Items", [])}
            return response(200, {
                "totalVectors": total_vectors,
                "totalUsers": len(user_pks),
                "requestId": request_id,
            })

        raise ApiError(404, "NOT_FOUND", "route not found")

    except ApiError as err:
        return error(err, request_id)
    except Exception:
        print(f"UNHANDLED ERROR requestId={request_id}\n{traceback.format_exc()}")
        return error(ApiError(500, "INTERNAL_ERROR", "internal server error"), request_id)
