"""RAG endpoints — Ask Your Data."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .deps import get_current_user
from ...core.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])


class AskRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class EmbedRequest(BaseModel):
    item_id: str = Field(..., alias="entryId")


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
async def ask_items(req: AskRequest, request: Request, user_id: str = Depends(get_current_user)):
    """Ask a question about your items. Returns an AI-generated answer with source citations."""
    check_rate_limit(user_id, "rag_ask")
    provider_name = request.headers.get("x-llm-provider") or None
    try:
        rag_service, _ = _get_rag_service()
        result = rag_service.ask(tenant_id=user_id, query=req.query, top_k=req.top_k, provider_name=provider_name)

        # Persist the Q&A exchange
        from ...core.repository import create_conversation
        sources_serializable = [
            {"entryId": s.get("entryId", ""), "title": s.get("title", ""),
             "snippet": s.get("snippet", ""), "score": s.get("score", 0),
             "createdAt": s.get("createdAt", "")}
            for s in (result.sources or [])
        ]
        try:
            create_conversation(
                user_id=user_id,
                question=req.query,
                answer=result.answer or "",
                sources=sources_serializable,
            )
        except Exception as store_err:
            logger.warning("Failed to store conversation: %s", store_err)

        return {
            "answer": result.answer,
            "sources": result.sources,
            "query": result.query,
        }
    except Exception as e:
        logger.error("RAG /ask failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "RAG_ERROR", "message": str(e)}) from e


@router.post("/search")
async def search_items(req: SearchRequest, user_id: str = Depends(get_current_user)):
    """Semantic search over items (no LLM generation, just matching entries)."""
    try:
        rag_service, _ = _get_rag_service()
        sources = rag_service.search_only(tenant_id=user_id, query=req.query, top_k=req.top_k)
        return {"results": sources, "query": req.query}
    except Exception as e:
        logger.error("RAG /search failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "RAG_ERROR", "message": str(e)}) from e


@router.post("/embed")
async def embed_item(req: EmbedRequest, user_id: str = Depends(get_current_user)):
    """Manually embed a specific item."""
    from ...core.repository import resolve_item

    _, retriever = _get_rag_service()
    item = resolve_item(user_id, req.item_id)
    if not item:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "item not found"})

    retriever.embed_entry(
        tenant_id=user_id,
        entry_id=item["entryId"],
        title=item["title"],
        body=item["body"],
        created_at=item["createdAt"],
    )
    return {"status": "embedded", "entryId": item["entryId"]}


@router.post("/embed-all")
async def embed_all_items(user_id: str = Depends(get_current_user)):
    """Embed all items for the current user. Used for initial setup or re-indexing."""
    check_rate_limit(user_id, "embed_all")
    try:
        from ...core.repository import list_items

        _, retriever = _get_rag_service()

        all_items = []
        next_token = None
        while True:
            # list_items returns a (items, next_token) tuple
            items, next_token = list_items(user_id, limit=100, next_token=next_token)
            all_items.extend(items)
            if not next_token:
                break

        embedded_count = 0
        for item in all_items:
            try:
                retriever.embed_entry(
                    tenant_id=user_id,
                    entry_id=item["entryId"],
                    title=item["title"],
                    body=item["body"],
                    created_at=item["createdAt"],
                )
                embedded_count += 1
            except Exception as e:
                logger.error("Failed to embed item %s: %s", item["entryId"], e)

        return {
            "status": "completed",
            "totalEntries": len(all_items),
            "embedded": embedded_count,
            "failed": len(all_items) - embedded_count,
        }
    except Exception as e:
        logger.error("RAG /embed-all failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "RAG_ERROR", "message": str(e)}) from e


@router.delete("/vectors")
async def delete_all_vectors(user_id: str = Depends(get_current_user)):
    """Delete all embeddings for the current user from the vector index."""
    try:
        _, retriever = _get_rag_service()
        retriever.store.delete_all(tenant_id=user_id)
        return {"deleted": True, "message": "All indexed entries removed."}
    except Exception as e:
        logger.error("RAG /vectors delete-all failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "RAG_ERROR", "message": str(e)}) from e


@router.get("/conversations")
async def list_conversations(user_id: str = Depends(get_current_user)):
    """List stored Ask conversation history for the current user."""
    from ...core.repository import list_conversations as _list_conversations
    try:
        items = _list_conversations(user_id)
        return {"items": items}
    except Exception as e:
        logger.error("RAG /conversations list failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "RAG_ERROR", "message": str(e)}) from e


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, user_id: str = Depends(get_current_user)):
    """Delete a stored conversation exchange."""
    from ...core.repository import delete_conversation as _delete_conversation
    try:
        ok = _delete_conversation(user_id, conv_id)
    except Exception as e:
        logger.error("RAG /conversations delete failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "RAG_ERROR", "message": str(e)}) from e
    if not ok:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "conversation not found"})
    return {"deleted": True}


@router.get("/status")
async def rag_status(user_id: str = Depends(get_current_user)):
    """Get embedding status for the current user."""
    try:
        _, retriever = _get_rag_service()
        count = retriever.count(tenant_id=user_id)
        return {"totalVectors": count, "userId": user_id}
    except Exception as e:
        logger.error("RAG /status failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "RAG_ERROR", "message": str(e)}) from e
