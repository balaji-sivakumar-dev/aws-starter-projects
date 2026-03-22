"""
FastAPI route handlers — thin layer that delegates all business logic to core/handlers.py.

Pattern:
  1. Parse / validate HTTP inputs (FastAPI does most of this via Pydantic)
  2. Call the corresponding core handler
  3. Catch AppError → HTTPException
  4. Return response dict
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ...core import handlers
from ...core.models import (
    AppError,
    CreateEntryRequest,
    ListEntriesResponse,
    SingleEntryResponse,
    UpdateEntryRequest,
)
from .deps import get_current_user, get_current_user_email

router = APIRouter()


def _rid(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid.uuid4()))


def _http(err: AppError) -> HTTPException:
    return HTTPException(
        status_code=err.status,
        detail={"code": err.code, "message": err.message},
    )


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["ops"])
def health():
    return handlers.health()


# ── Identity ──────────────────────────────────────────────────────────────────

@router.get("/me", tags=["auth"])
def me(
    request: Request,
    user_id: str = Depends(get_current_user),
    email: str = Depends(get_current_user_email),
):
    return {**handlers.me(user_id, email), "requestId": _rid(request)}


# ── Entries ───────────────────────────────────────────────────────────────────

class BulkDeleteRequest(BaseModel):
    entryIds: List[str]


@router.get("/entries", response_model=ListEntriesResponse, tags=["entries"])
def list_entries(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    nextToken: Optional[str] = Query(default=None),
    user_id: str = Depends(get_current_user),
):
    try:
        items, next_tok = handlers.list_entries(user_id, limit, nextToken)
    except AppError as exc:
        raise _http(exc)
    return {"items": items, "nextToken": next_tok, "requestId": _rid(request)}


# NOTE: static sub-paths (/count, /bulk-delete) must be registered BEFORE
# the parameterised route /entries/{entry_id} to avoid FastAPI swallowing
# "count" and "bulk-delete" as path parameter values.

@router.get("/entries/count", tags=["entries"])
def count_entries(
    request: Request,
    user_id: str = Depends(get_current_user),
):
    count = handlers.count_entries(user_id)
    return {"count": count, "requestId": _rid(request)}


@router.post("/entries/bulk-delete", tags=["entries"])
def bulk_delete_entries(
    body: BulkDeleteRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    try:
        deleted = handlers.bulk_delete_entries(user_id, body.entryIds)
    except AppError as exc:
        raise _http(exc)
    return {"deleted": deleted, "requestId": _rid(request)}


@router.post("/entries", response_model=SingleEntryResponse, status_code=201, tags=["entries"])
def create_entry(
    body: CreateEntryRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    try:
        item = handlers.create_entry(user_id, body.title, body.body)
    except AppError as exc:
        raise _http(exc)
    return {"item": item, "requestId": _rid(request)}


@router.get("/entries/{entry_id}", response_model=SingleEntryResponse, tags=["entries"])
def get_entry(
    entry_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    try:
        item = handlers.get_entry(user_id, entry_id)
    except AppError as exc:
        raise _http(exc)
    return {"item": item, "requestId": _rid(request)}


@router.put("/entries/{entry_id}", response_model=SingleEntryResponse, tags=["entries"])
def update_entry(
    entry_id: str,
    body: UpdateEntryRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    try:
        item = handlers.update_entry(user_id, entry_id, body.title, body.body)
    except AppError as exc:
        raise _http(exc)
    return {"item": item, "requestId": _rid(request)}


@router.delete("/entries/{entry_id}", tags=["entries"])
def delete_entry(
    entry_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    try:
        handlers.delete_entry(user_id, entry_id)
    except AppError as exc:
        raise _http(exc)
    return {"deleted": True, "requestId": _rid(request)}


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/entries/{entry_id}/ai", status_code=202, tags=["ai"])
def trigger_ai(
    entry_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    provider_name = request.headers.get("x-llm-provider") or None
    try:
        result = handlers.trigger_ai(user_id, entry_id, provider_name=provider_name)
    except AppError as exc:
        raise _http(exc)
    return {**result, "requestId": _rid(request)}
