import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import get_current_user
from .models import (
    CreateEntryRequest,
    ListEntriesResponse,
    SingleEntryResponse,
    UpdateEntryRequest,
)
from . import repository

router = APIRouter()


def _rid(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid.uuid4()))


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["ops"])
def health():
    return {"status": "ok"}


# ── Identity ──────────────────────────────────────────────────────────────────

@router.get("/me", tags=["auth"])
def me(request: Request, user_id: str = Depends(get_current_user)):
    return {"userId": user_id, "requestId": _rid(request)}


# ── Journal entries ───────────────────────────────────────────────────────────

@router.get("/entries", response_model=ListEntriesResponse, tags=["entries"])
def list_entries(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    nextToken: Optional[str] = Query(default=None),
    user_id: str = Depends(get_current_user),
):
    try:
        items, next_tok = repository.list_entries(user_id, limit, nextToken)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": str(exc)},
        )
    return {"items": items, "nextToken": next_tok, "requestId": _rid(request)}


@router.post("/entries", response_model=SingleEntryResponse, status_code=201, tags=["entries"])
def create_entry(
    body: CreateEntryRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    title = body.title.strip()
    content = body.body.strip()
    if not title:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": "title is required"},
        )
    if not content:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": "body is required"},
        )
    item = repository.create_entry(user_id, title, content)
    return {"item": repository.to_entry(item), "requestId": _rid(request)}


@router.get("/entries/{entry_id}", response_model=SingleEntryResponse, tags=["entries"])
def get_entry(
    entry_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    item = repository.resolve_entry(user_id, entry_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "entry not found"},
        )
    return {"item": repository.to_entry(item), "requestId": _rid(request)}


@router.put("/entries/{entry_id}", response_model=SingleEntryResponse, tags=["entries"])
def update_entry(
    entry_id: str,
    body: UpdateEntryRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    title = body.title.strip() if body.title is not None else None
    content = body.body.strip() if body.body is not None else None

    if title is not None and not title:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": "title cannot be empty"},
        )
    if content is not None and not content:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": "body cannot be empty"},
        )
    if title is None and content is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": "nothing to update"},
        )

    updated = repository.update_entry(user_id, entry_id, title, content)
    if not updated:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "entry not found"},
        )
    return {"item": repository.to_entry(updated), "requestId": _rid(request)}


@router.delete("/entries/{entry_id}", tags=["entries"])
def delete_entry(
    entry_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    deleted = repository.soft_delete_entry(user_id, entry_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "entry not found"},
        )
    return {"deleted": True, "requestId": _rid(request)}


# ── AI workflow ───────────────────────────────────────────────────────────────

@router.post("/entries/{entry_id}/ai", status_code=202, tags=["ai"])
def trigger_ai(
    entry_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """
    Enqueue an AI enrichment job for the entry (summary + tags).

    Local mode: returns a stub response — no Step Functions call is made.
    AWS mode (Phase 4): will start a Step Functions execution.
    """
    item = repository.resolve_entry(user_id, entry_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "entry not found"},
        )
    # TODO (Phase 4): trigger Step Functions / async AI pipeline here
    return {
        "entryId": entry_id,
        "aiStatus": "QUEUED",
        "requestId": _rid(request),
        "note": "AI pipeline not yet wired — coming in Phase 4",
    }
