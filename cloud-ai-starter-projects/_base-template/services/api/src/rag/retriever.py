"""
Retriever — orchestrates embedding queries and vector search.
"""

import logging

from .embedding import EmbeddingProvider
from .store import SearchResult, VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Embeds a query and searches the vector store for similar documents."""

    def __init__(self, embedding_provider: EmbeddingProvider, vector_store: VectorStore) -> None:
        self.embedder = embedding_provider
        self.store = vector_store

    def search(self, tenant_id: str, query: str, top_k: int = 5) -> list[SearchResult]:
        """Embed a query and return the top-k most similar documents."""
        query_vector = self.embedder.embed(query)
        results = self.store.search(tenant_id, query_vector, top_k=top_k)
        logger.info(
            "Retriever search: tenant=%s query='%s' results=%d",
            tenant_id, query[:60], len(results),
        )
        return results

    def embed_entry(self, tenant_id: str, entry_id: str, title: str,
                    body: str, created_at: str) -> None:
        """Embed a item and store it in the vector store."""
        text = f"{title}\n\n{body}"
        vector = self.embedder.embed(text)
        metadata = {
            "entryId": entry_id,
            "title": title,
            "createdAt": created_at,
        }
        self.store.upsert(tenant_id, entry_id, vector, metadata, text)
        logger.info("Embedded entry=%s for tenant=%s", entry_id, tenant_id)

    def remove_entry(self, tenant_id: str, entry_id: str) -> None:
        """Remove an entry's embedding from the vector store."""
        self.store.delete(tenant_id, entry_id)

    def count(self, tenant_id: str) -> int:
        """Count total embedded documents for a tenant."""
        return self.store.count(tenant_id)
