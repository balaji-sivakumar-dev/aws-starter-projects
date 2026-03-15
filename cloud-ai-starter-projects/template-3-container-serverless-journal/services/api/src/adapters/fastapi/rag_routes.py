"""RAG endpoints — Ask Your Journal."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])


class AskRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class EmbedRequest(BaseModel):
    entry_id: str = Field(..., alias="entryId")


def _get_rag_service():
    """Lazy-init the RAG service (only when RAG endpoints are called)."""
    from ...rag.embedding_factory import get_embedding_provider
    from ...rag.retriever import Retriever
    from ...rag.rag_service import RAGService
    from ...rag.store_factory import get_vector_store

    store = get_vector_store()
    embedder = get_embedding_provider()
    retriever = Retriever(embedder, store)
    return RAGService(retriever), retriever


@router.post("/ask")
async def ask_journal(req: AskRequest, user_id: str = Depends(get_current_user)):
    """Ask a question about your journal entries. Returns an AI-generated answer with source citations."""
    rag_service, _ = _get_rag_service()
    result = rag_service.ask(tenant_id=user_id, query=req.query, top_k=req.top_k)
    return {
        "answer": result.answer,
        "sources": result.sources,
        "query": result.query,
    }


@router.post("/search")
async def search_journal(req: SearchRequest, user_id: str = Depends(get_current_user)):
    """Semantic search over journal entries (no LLM generation, just matching entries)."""
    rag_service, _ = _get_rag_service()
    sources = rag_service.search_only(tenant_id=user_id, query=req.query, top_k=req.top_k)
    return {"results": sources, "query": req.query}


@router.post("/embed")
async def embed_entry(req: EmbedRequest, user_id: str = Depends(get_current_user)):
    """Manually embed a specific journal entry."""
    from ...core.repository import resolve_entry

    _, retriever = _get_rag_service()
    entry = resolve_entry(user_id, req.entry_id)
    if not entry:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "entry not found"})

    retriever.embed_entry(
        tenant_id=user_id,
        entry_id=entry["entryId"],
        title=entry["title"],
        body=entry["body"],
        created_at=entry["createdAt"],
    )
    return {"status": "embedded", "entryId": entry["entryId"]}


@router.post("/embed-all")
async def embed_all_entries(user_id: str = Depends(get_current_user)):
    """Embed all journal entries for the current user. Used for initial setup or re-indexing."""
    from ...core.repository import list_entries

    _, retriever = _get_rag_service()

    all_entries = []
    next_token = None
    while True:
        result = list_entries(user_id, limit=100, next_token=next_token)
        all_entries.extend(result["items"])
        next_token = result.get("nextToken")
        if not next_token:
            break

    embedded_count = 0
    for entry in all_entries:
        try:
            retriever.embed_entry(
                tenant_id=user_id,
                entry_id=entry["entryId"],
                title=entry["title"],
                body=entry["body"],
                created_at=entry["createdAt"],
            )
            embedded_count += 1
        except Exception as e:
            logger.error("Failed to embed entry %s: %s", entry["entryId"], e)

    return {
        "status": "completed",
        "totalEntries": len(all_entries),
        "embedded": embedded_count,
        "failed": len(all_entries) - embedded_count,
    }


@router.get("/status")
async def rag_status(user_id: str = Depends(get_current_user)):
    """Get embedding status for the current user."""
    _, retriever = _get_rag_service()
    count = retriever.count(tenant_id=user_id)
    return {"totalVectors": count, "userId": user_id}
