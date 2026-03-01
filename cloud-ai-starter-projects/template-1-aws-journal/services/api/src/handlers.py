import json
import os
from typing import Any, Dict

import boto3

from errors import ApiError, build_response, error_response
from models import to_entry_response, to_limit, validate_create_payload, validate_update_payload
from repository import create_entry, get_entry, list_entries, mark_ai_queued, soft_delete_entry, update_entry

sfn = boto3.client("stepfunctions")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    request_id = _request_id(event, context)

    try:
        method, path = _method_path(event)
        claims = _claims(event)

        if method == "GET" and path == "/health":
            return build_response(200, {"status": "ok", "requestId": request_id})

        if method == "GET" and path == "/me":
            user_id = _require_user_id(claims)
            return build_response(
                200,
                {
                    "userId": user_id,
                    "email": claims.get("email"),
                    "requestId": request_id,
                },
            )

        if method == "GET" and path == "/entries":
            user_id = _require_user_id(claims)
            params = event.get("queryStringParameters") or {}
            limit = to_limit(params.get("limit"))
            items, next_token = list_entries(user_id, limit, params.get("nextToken"))
            return build_response(
                200,
                {
                    "items": [to_entry_response(item) for item in items],
                    "nextToken": next_token,
                    "requestId": request_id,
                },
            )

        if method == "POST" and path == "/entries":
            user_id = _require_user_id(claims)
            payload = _json_body(event)
            validated = validate_create_payload(payload)
            item = create_entry(user_id, validated["title"], validated["body"])
            return build_response(201, {"item": to_entry_response(item), "requestId": request_id})

        entry_id = _entry_id(event)

        if method == "GET" and _matches_entry_path(path):
            user_id = _require_user_id(claims)
            item = get_entry(user_id, entry_id)
            return build_response(200, {"item": to_entry_response(item), "requestId": request_id})

        if method == "PUT" and _matches_entry_path(path):
            user_id = _require_user_id(claims)
            payload = _json_body(event)
            updates = validate_update_payload(payload)
            item = update_entry(user_id, entry_id, updates)
            return build_response(200, {"item": to_entry_response(item), "requestId": request_id})

        if method == "DELETE" and _matches_entry_path(path):
            user_id = _require_user_id(claims)
            soft_delete_entry(user_id, entry_id)
            return build_response(200, {"deleted": True, "requestId": request_id})

        if method == "POST" and path.endswith("/ai"):
            user_id = _require_user_id(claims)
            mark_ai_queued(user_id, entry_id)
            execution = sfn.start_execution(
                stateMachineArn=os.environ["WORKFLOW_ARN"],
                input=json.dumps(
                    {
                        "userId": user_id,
                        "entryId": entry_id,
                        "requestId": request_id,
                    }
                ),
                name=f"{entry_id}-{request_id}".replace("-", "")[:80],
            )
            return build_response(
                202,
                {
                    "entryId": entry_id,
                    "aiStatus": "QUEUED",
                    "executionArn": execution["executionArn"],
                    "requestId": request_id,
                },
            )

        raise ApiError(404, "NOT_FOUND", "route not found")

    except ApiError as err:
        return error_response(err, request_id)
    except Exception:  # noqa: BLE001
        return error_response(ApiError(500, "INTERNAL_ERROR", "internal server error"), request_id)


def _request_id(event: Dict[str, Any], context: Any) -> str:
    return (
        (event.get("requestContext") or {}).get("requestId")
        or getattr(context, "aws_request_id", None)
        or "unknown-request-id"
    )


def _method_path(event: Dict[str, Any]) -> tuple[str, str]:
    request_context = event.get("requestContext") or {}
    http = request_context.get("http") or {}
    method = str(http.get("method") or event.get("httpMethod") or "GET").upper()
    path = str(http.get("path") or event.get("rawPath") or event.get("path") or "/")
    return method, path


def _claims(event: Dict[str, Any]) -> Dict[str, Any]:
    authorizer = ((event.get("requestContext") or {}).get("authorizer") or {})
    jwt = authorizer.get("jwt") or {}
    claims = jwt.get("claims") or {}
    return claims


def _require_user_id(claims: Dict[str, Any]) -> str:
    user_id = str(claims.get("sub") or "")
    if not user_id:
        raise ApiError(401, "UNAUTHORIZED", "missing valid token")
    return user_id


def _json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raise ApiError(400, "VALIDATION_ERROR", "base64 body not supported")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError(400, "VALIDATION_ERROR", "invalid JSON body") from exc
    if not isinstance(data, dict):
        raise ApiError(400, "VALIDATION_ERROR", "JSON body must be an object")
    return data


def _entry_id(event: Dict[str, Any]) -> str:
    path_params = event.get("pathParameters") or {}
    entry_id = str(path_params.get("entryId") or "").strip()
    if not entry_id:
        raise ApiError(400, "VALIDATION_ERROR", "entryId is required")
    return entry_id


def _matches_entry_path(path: str) -> bool:
    parts = [p for p in path.split("/") if p]
    return len(parts) == 2 and parts[0] == "entries"
