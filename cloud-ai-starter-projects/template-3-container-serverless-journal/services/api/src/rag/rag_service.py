"""
RAG service — retrieval-augmented generation for journal queries.

Combines vector retrieval with LLM completion to answer user questions
about their journal entries with source citations.
"""

import logging
from dataclasses import dataclass, field

from .retriever import Retriever
from .store import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RAGAnswer:
    """Response from a RAG query."""
    answer: str
    sources: list[dict] = field(default_factory=list)
    query: str = ""


class RAGService:
    """Orchestrates retrieval + LLM generation for conversational journal queries."""

    def __init__(self, retriever: Retriever) -> None:
        self.retriever = retriever

    def ask(self, tenant_id: str, query: str, top_k: int = 5, provider_name: str | None = None) -> RAGAnswer:
        """
        Answer a user's question using their journal entries as context.

        1. Retrieve the most relevant entries via semantic search
        2. Build a prompt with the retrieved context
        3. Generate an answer using the LLM
        4. Return the answer with source citations
        """
        results = self.retriever.search(tenant_id, query, top_k=top_k)

        if not results:
            return RAGAnswer(
                answer="I don't have enough journal entries to answer that question. "
                       "Try writing more entries or embedding your existing ones first.",
                sources=[],
                query=query,
            )

        context = self._build_context(results)
        answer = self._generate_answer(query, context, provider_name=provider_name)
        sources = self._format_sources(results)

        return RAGAnswer(answer=answer, sources=sources, query=query)

    def search_only(self, tenant_id: str, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search without LLM generation — returns matching entries."""
        results = self.retriever.search(tenant_id, query, top_k=top_k)
        return self._format_sources(results)

    def _build_context(self, results: list[SearchResult]) -> str:
        """Format retrieved documents as context for the LLM prompt."""
        parts = []
        for i, r in enumerate(results, 1):
            date = r.metadata.get("createdAt", "unknown date")[:10]
            title = r.metadata.get("title", "Untitled")
            parts.append(f"[Entry {i} — {date}: {title}]\n{r.text}")
        return "\n\n---\n\n".join(parts)

    def _generate_answer(self, query: str, context: str, provider_name: str | None = None) -> str:
        """Use the LLM to generate an answer from the retrieved context."""
        import os

        prompt = (
            "You are a personal journal assistant. The user is asking a question about "
            "their own journal entries. Use ONLY the journal entries provided below to "
            "answer. If the entries don't contain enough information, say so honestly.\n\n"
            "Be warm, reflective, and insightful. Reference specific entries by date "
            "when relevant. Keep your answer concise (2-4 paragraphs max).\n\n"
            f"--- JOURNAL ENTRIES ---\n\n{context}\n\n"
            f"--- USER QUESTION ---\n\n{query}\n\n"
            "--- YOUR ANSWER ---"
        )

        raw = ""

        # Try the configured LLM provider first
        try:
            from src.llm.factory import get_provider
            provider = get_provider(provider_name)
            if hasattr(provider, "_chat"):
                raw = provider._chat(prompt)
        except Exception as e:
            logger.warning("LLM provider failed, will try Ollama fallback: %s", e)

        # Fallback: direct Ollama client
        if not raw:
            try:
                import ollama
                host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
                model = os.getenv("OLLAMA_MODEL", "llama3.2")
                client = ollama.Client(host=host)
                response = client.chat(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.4},
                )
                raw = response["message"]["content"]
            except Exception as e:
                logger.error("RAG LLM generation failed (all methods): %s", e)
                raw = ("Based on the journal entries I found, here are the relevant passages. "
                       "However, I couldn't generate a full answer — please check your LLM configuration.")

        logger.info("RAG answer generated: query='%s' answer_len=%d", query[:60], len(raw))
        return raw.strip()

    def _format_sources(self, results: list[SearchResult]) -> list[dict]:
        """Format search results as source citations."""
        return [
            {
                "entryId": r.metadata.get("entryId", r.doc_id),
                "title": r.metadata.get("title", "Untitled"),
                "createdAt": r.metadata.get("createdAt", ""),
                "score": round(r.score, 4),
                "snippet": r.text[:200] + ("..." if len(r.text) > 200 else ""),
            }
            for r in results
        ]
