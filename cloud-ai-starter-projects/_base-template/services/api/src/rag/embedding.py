"""
Embedding provider interface and implementations.

All embedding providers implement the EmbeddingProvider ABC so the rest
of the codebase never depends on a specific SDK.

EMBEDDING_PROVIDER values:
  ollama  →  local Ollama server  (default model: nomic-embed-text)
  titan   →  Amazon Titan Embeddings v2 via Bedrock  ($0.020/1M tokens)
  openai  →  OpenAI text-embedding-3-small           ($0.020/1M tokens, same cost)

Usage:
    from src.rag.embedding_factory import get_embedding_provider
    provider = get_embedding_provider()
    vector = provider.embed("Some text to embed")
"""

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for all embedding providers."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text string."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the dimensionality of the embedding vectors."""


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding via local Ollama server using nomic-embed-text."""

    DEFAULT_MODEL = "nomic-embed-text"
    DEFAULT_HOST = "http://localhost:11434"

    def __init__(self) -> None:
        import ollama  # lazy import

        self.model = os.getenv("EMBEDDING_MODEL", self.DEFAULT_MODEL)
        host = os.getenv("OLLAMA_HOST", self.DEFAULT_HOST)
        self.client = ollama.Client(host=host)
        self._dimensions = 768  # nomic-embed-text default
        logger.info("OllamaEmbeddingProvider initialised (host=%s, model=%s)", host, self.model)

    def embed(self, text: str) -> list[float]:
        response = self.client.embed(model=self.model, input=text)
        # ollama>=0.4 returns an EmbedResponse object with .embeddings attribute
        # older versions return a dict with "embeddings" or "embedding" key
        if hasattr(response, "embeddings"):
            embeddings = response.embeddings
        elif isinstance(response, dict):
            embeddings = response.get("embeddings") or response.get("embedding")
        else:
            embeddings = response
        if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
            return embeddings[0]
        return embeddings

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            results.append(self.embed(text))
        return results

    @property
    def dimensions(self) -> int:
        return self._dimensions


class TitanEmbeddingProvider(EmbeddingProvider):
    """Embedding via Amazon Titan Embeddings v2 (Bedrock)."""

    DEFAULT_MODEL = "amazon.titan-embed-text-v2:0"

    def __init__(self) -> None:
        import boto3  # lazy import
        import json  # noqa: F811

        self.model = os.getenv("EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self.client = boto3.client("bedrock-runtime")
        self._json = json
        self._dimensions = 1024  # titan-embed-text-v2 default
        logger.info("TitanEmbeddingProvider initialised (model=%s)", self.model)

    def embed(self, text: str) -> list[float]:
        response = self.client.invoke_model(
            modelId=self.model,
            body=self._json.dumps({"inputText": text}),
            contentType="application/json",
            accept="application/json",
        )
        body = self._json.loads(response["body"].read())
        return body["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    @property
    def dimensions(self) -> int:
        return self._dimensions


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding via OpenAI text-embedding-3-small (or configurable model)."""

    DEFAULT_MODEL = "text-embedding-3-small"

    def __init__(self) -> None:
        from openai import OpenAI  # lazy import

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI embedding provider")

        self.model = os.getenv("OPENAI_EMBED_MODEL", self.DEFAULT_MODEL)
        self.client = OpenAI(api_key=api_key)
        # text-embedding-3-small → 1536 dims by default
        self._dimensions = 1536
        logger.info("OpenAIEmbeddingProvider initialised (model=%s)", self.model)

    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]

    @property
    def dimensions(self) -> int:
        return self._dimensions
