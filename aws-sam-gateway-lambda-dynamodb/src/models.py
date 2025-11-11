from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TodoCreate(BaseModel):
    title: str = Field(min_length=1)
    description: Optional[str] = None
    status: str = Field(default="pending")  # pending|done

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class TodoItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str = "pending"
    created_at: str
    updated_at: str

    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"
