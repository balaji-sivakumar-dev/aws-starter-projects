"""
Direct Lambda adapter — no web framework overhead.

Parses Lambda HTTP API v2 events, resolves auth via core/auth.py,
delegates business logic to core/handlers.py, and formats Lambda responses.

Use this for:
  - Lambda zip deployments (smallest cold start, no FastAPI)
  - Situations where you want minimal dependencies in the Lambda package

Entry point:  src.lambda_handler.handler  (see top-level lambda_handler.py)
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

from ...core import auth as core_auth
from ...core import handlers
from ...core.models import AppError

logger = logging.getLogger(__name__)
APP_ENV = os.getenv("APP_ENV", "local")


# ── Response helpers ──────────────────────────────────────────────────────────

def _cors_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "*",
    }


def _ok(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {"statusCode": status, "headers": _cors_headers(), "body": json.dumps(body)}


def _err(status: int, code: str, message: str, request_id: str) -> Dict[str, Any]:
    return _ok(status, {"code": code, "message": message, "requestId": request_id})


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_user_id(event: Dict[str, Any]) -> str:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}

    if APP_ENV == "local":
        return core_auth.resolve_user_local(headers.get("x-user-id"))

    auth_header = headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise AppError(401, "UNAUTHORIZED", "missing valid token")
    try:
        return core_auth.resolve_user_cognito(auth_header.removeprefix("Bearer ").strip())
    except ValueError as exc:
        raise AppError(401, "UNAUTHORIZED", str(exc)) from exc


# ── Routing ───────────────────────────────────────────────────────────────────

def _parse_event(event: Dict[str, Any]):
    http = (event.get("requestContext") or {}).get("http") or {}
    method = str(http.get("method") or "GET").upper()
    path = str(http.get("path") or "/").rstrip("/") or "/"
    query = event.get("queryStringParameters") or {}
    path_params = event.get("pathParameters") or {}
    raw_body = event.get("body") or "{}"
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        body = {}
    return method, path, query, path_params, body


def _request_id(event: Dict[str, Any]) -> str:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    return (
        headers.get("x-request-id")
        or (event.get("requestContext") or {}).get("requestId")
        or str(uuid.uuid4())
    )


def dispatch(event: Dict[str, Any]) -> Dict[str, Any]:
    rid = _request_id(event)

    try:
        method, path, query, path_params, body = _parse_event(event)

        # Public routes (no auth)
        if method == "GET" and path == "/health":
            return _ok(200, {**handlers.health(), "requestId": rid})

        # Auth for all other routes
        user_id = _get_user_id(event)

        # /me
        if method == "GET" and path == "/me":
            return _ok(200, {**handlers.me(user_id), "requestId": rid})

        # /entries
        if method == "GET" and path == "/entries":
            limit = max(1, min(int(query.get("limit") or 20), 100))
            items, next_tok = handlers.list_items(user_id, limit, query.get("nextToken"))
            return _ok(200, {"items": items, "nextToken": next_tok, "requestId": rid})

        if method == "POST" and path == "/entries":
            item = handlers.create_item(user_id, str(body.get("title") or ""), str(body.get("body") or ""))
            return _ok(201, {"item": item, "requestId": rid})

        # /entries/{entryId}
        item_id = path_params.get("entryId") or path.rsplit("/", 1)[-1]

        if method == "GET":
            item = handlers.get_item(user_id, item_id)
            return _ok(200, {"item": item, "requestId": rid})

        if method == "PUT":
            title: Optional[str] = body.get("title")
            content: Optional[str] = body.get("body")
            item = handlers.update_item(user_id, item_id, title, content)
            return _ok(200, {"item": item, "requestId": rid})

        if method == "DELETE":
            handlers.delete_item(user_id, item_id)
            return _ok(200, {"deleted": True, "requestId": rid})

        if method == "POST" and path.endswith("/ai"):
            result = handlers.trigger_ai(user_id, item_id)
            return _ok(202, {**result, "requestId": rid})

        raise AppError(404, "NOT_FOUND", "route not found")

    except AppError as exc:
        return _err(exc.status, exc.code, exc.message, rid)
    except Exception as exc:
        logger.exception("Unhandled error: %s", exc)
        return _err(500, "INTERNAL_ERROR", "internal server error", rid)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry point."""
    return dispatch(event)
