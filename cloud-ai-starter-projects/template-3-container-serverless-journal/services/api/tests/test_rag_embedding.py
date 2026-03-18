"""
Unit tests for OllamaEmbeddingProvider.embed() — FIX-004 coverage.

Tests verify that the embedding method correctly handles both:
  - ollama>=0.4 EmbedResponse objects (with .embeddings attribute)
  - older dict-style responses (with "embeddings" or "embedding" key)
  - nested list responses (batch format [[v1, v2, ...]])
  - flat list responses (single vector [v1, v2, ...])

No real Ollama server is required — the client.embed() call is mocked.

Run:
    cd services/api
    pytest tests/test_rag_embedding.py -v
"""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Set required env vars before importing the module
os.environ.setdefault("EMBEDDING_MODEL", "nomic-embed-text")
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_VECTOR = [0.1, 0.2, 0.3, 0.4, 0.5]


def _make_provider():
    """Create an OllamaEmbeddingProvider with a mocked ollama.Client."""
    with patch("ollama.Client") as mock_client_cls:
        mock_client_cls.return_value = MagicMock()
        from src.rag.embedding import OllamaEmbeddingProvider
        provider = OllamaEmbeddingProvider()
        return provider


# ---------------------------------------------------------------------------
# Response format: object with .embeddings attribute (ollama>=0.4)
# ---------------------------------------------------------------------------

class TestOllamaObjectResponse:
    """ollama>=0.4 returns an EmbedResponse object, not a dict."""

    def test_embed_returns_flat_vector_from_nested_embeddings(self):
        """EmbedResponse.embeddings is a list of vectors — we return the first."""
        provider = _make_provider()
        provider.client.embed.return_value = SimpleNamespace(
            embeddings=[FAKE_VECTOR]
        )
        result = provider.embed("hello world")
        assert result == FAKE_VECTOR

    def test_embed_returns_flat_vector_when_embeddings_already_flat(self):
        """If embeddings is a flat list of floats, return it as-is."""
        provider = _make_provider()
        provider.client.embed.return_value = SimpleNamespace(
            embeddings=FAKE_VECTOR  # flat, not nested
        )
        result = provider.embed("hello world")
        assert result == FAKE_VECTOR

    def test_embed_passes_correct_model_and_input(self):
        """Verify model name and input text are forwarded to client.embed()."""
        provider = _make_provider()
        provider.client.embed.return_value = SimpleNamespace(embeddings=[FAKE_VECTOR])
        provider.embed("test text")
        provider.client.embed.assert_called_once_with(
            model="nomic-embed-text", input="test text"
        )


# ---------------------------------------------------------------------------
# Response format: dict (ollama<0.4)
# ---------------------------------------------------------------------------

class TestOllamaDictResponse:
    """Older ollama versions return a plain dict."""

    def test_embed_handles_dict_with_embeddings_key(self):
        provider = _make_provider()
        provider.client.embed.return_value = {"embeddings": [FAKE_VECTOR]}
        result = provider.embed("hello world")
        assert result == FAKE_VECTOR

    def test_embed_handles_dict_with_embedding_key(self):
        """Some versions use singular 'embedding' key."""
        provider = _make_provider()
        provider.client.embed.return_value = {"embedding": FAKE_VECTOR}
        result = provider.embed("test")
        assert result == FAKE_VECTOR

    def test_embed_handles_dict_flat_embeddings(self):
        """Dict with embeddings as flat list (not nested)."""
        provider = _make_provider()
        provider.client.embed.return_value = {"embeddings": FAKE_VECTOR}
        result = provider.embed("test")
        assert result == FAKE_VECTOR


# ---------------------------------------------------------------------------
# Batch embedding
# ---------------------------------------------------------------------------

class TestEmbedBatch:
    def test_embed_batch_returns_one_vector_per_text(self):
        provider = _make_provider()
        provider.client.embed.return_value = SimpleNamespace(embeddings=[FAKE_VECTOR])
        texts = ["entry one", "entry two", "entry three"]
        results = provider.embed_batch(texts)
        assert len(results) == 3
        assert all(r == FAKE_VECTOR for r in results)

    def test_embed_batch_calls_embed_for_each_text(self):
        provider = _make_provider()
        provider.client.embed.return_value = SimpleNamespace(embeddings=[FAKE_VECTOR])
        provider.embed_batch(["a", "b"])
        assert provider.client.embed.call_count == 2

    def test_embed_batch_empty_input_returns_empty_list(self):
        provider = _make_provider()
        results = provider.embed_batch([])
        assert results == []


# ---------------------------------------------------------------------------
# Provider properties
# ---------------------------------------------------------------------------

class TestProviderProperties:
    def test_dimensions_returns_768_for_nomic_embed_text(self):
        provider = _make_provider()
        assert provider.dimensions == 768

    def test_model_uses_env_var(self):
        with patch.dict(os.environ, {"EMBEDDING_MODEL": "custom-model"}):
            # Re-import to pick up the env var
            with patch("ollama.Client"):
                from importlib import reload
                import src.rag.embedding as emb_module
                reload(emb_module)
                provider = emb_module.OllamaEmbeddingProvider()
                assert provider.model == "custom-model"
