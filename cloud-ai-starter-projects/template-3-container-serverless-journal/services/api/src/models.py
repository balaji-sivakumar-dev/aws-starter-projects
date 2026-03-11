from typing import List, Optional

from pydantic import BaseModel


class CreateEntryRequest(BaseModel):
    title: str
    body: str


class UpdateEntryRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None


class EntryOut(BaseModel):
    entryId: str
    userId: str
    title: str
    body: str
    createdAt: str
    updatedAt: str
    deletedAt: Optional[str] = None
    aiStatus: str = "NOT_REQUESTED"
    summary: Optional[str] = None
    tags: List[str] = []
    aiUpdatedAt: Optional[str] = None
    aiError: Optional[str] = None


class SingleEntryResponse(BaseModel):
    item: EntryOut
    requestId: str


class ListEntriesResponse(BaseModel):
    items: List[EntryOut]
    nextToken: Optional[str] = None
    requestId: str
