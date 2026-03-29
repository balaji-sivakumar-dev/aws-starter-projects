from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Domain error ──────────────────────────────────────────────────────────────

class AppError(Exception):
    """Raised by core handlers; adapters map this to their error format."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


# ── Request models ────────────────────────────────────────────────────────────
# Replace "Item" with your domain entity name (e.g., Transaction, Task, Note).

class CreateItemRequest(BaseModel):
    title: str
    body: str
    entryDate: Optional[str] = None
    data: Dict[str, Any] = {}


class UpdateItemRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    entryDate: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class BulkImportItemIn(BaseModel):
    title: str
    body: str
    entryDate: Optional[str] = None
    data: Dict[str, Any] = {}


class BulkImportRequest(BaseModel):
    entries: List["BulkImportItemIn"]


# ── Response models ───────────────────────────────────────────────────────────

class ItemOut(BaseModel):
    itemId: str
    userId: str
    title: str
    body: str
    entryDate: Optional[str] = None
    data: Dict[str, Any] = {}
    createdAt: str
    updatedAt: str
    deletedAt: Optional[str] = None
    aiStatus: str = "NOT_REQUESTED"
    summary: Optional[str] = None
    tags: List[str] = []
    aiUpdatedAt: Optional[str] = None
    aiError: Optional[str] = None


class SingleItemResponse(BaseModel):
    item: ItemOut
    requestId: str = ""


class ListItemsResponse(BaseModel):
    items: List[ItemOut]
    nextToken: Optional[str] = None
    requestId: str = ""
