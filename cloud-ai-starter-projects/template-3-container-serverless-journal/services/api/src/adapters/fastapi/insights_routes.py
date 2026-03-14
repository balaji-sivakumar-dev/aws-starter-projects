"""
FastAPI routes for the AI Insights (period summaries) layer.

Endpoints:
  GET    /insights/summaries                       list all summaries
  POST   /insights/summaries                       generate a new summary
  GET    /insights/summaries/{summary_id}          get one summary
  DELETE /insights/summaries/{summary_id}          delete a summary
  POST   /insights/summaries/{summary_id}/regenerate  regenerate with LLM
"""

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ...core import insights
from ...core.models import AppError
from .deps import get_current_user

router = APIRouter(prefix="/insights", tags=["insights"])


def _rid(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid.uuid4()))


def _http(err: AppError) -> HTTPException:
    return HTTPException(
        status_code=err.status,
        detail={"code": err.code, "message": err.message},
    )


class GenerateSummaryRequest(BaseModel):
    period: Literal["weekly", "monthly", "yearly"]
    year: int
    week: Optional[int] = None
    month: Optional[int] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/summaries")
def list_summaries(
    request: Request,
    user_id: str = Depends(get_current_user),
):
    items = insights.list_summaries(user_id)
    return {"items": items, "requestId": _rid(request)}


@router.post("/summaries", status_code=201)
def generate_summary(
    body: GenerateSummaryRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    try:
        item = insights.generate_summary(
            user_id=user_id,
            period=body.period,
            year=body.year,
            week=body.week,
            month=body.month,
        )
    except AppError as exc:
        raise _http(exc)
    return {"item": item, "requestId": _rid(request)}


@router.get("/summaries/{summary_id}")
def get_summary(
    summary_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    try:
        item = insights.get_summary(user_id, summary_id)
    except AppError as exc:
        raise _http(exc)
    return {"item": item, "requestId": _rid(request)}


@router.delete("/summaries/{summary_id}")
def delete_summary(
    summary_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    try:
        insights.delete_summary(user_id, summary_id)
    except AppError as exc:
        raise _http(exc)
    return {"deleted": True, "requestId": _rid(request)}


@router.post("/summaries/{summary_id}/regenerate")
def regenerate_summary(
    summary_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    try:
        item = insights.regenerate_summary(user_id, summary_id)
    except AppError as exc:
        raise _http(exc)
    return {"item": item, "requestId": _rid(request)}
