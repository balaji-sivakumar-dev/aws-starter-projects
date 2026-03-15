"""
Embedding provider factory.

Reads EMBEDDING_PROVIDER from the environment and returns the appropriate provider.
Providers are imported lazily so unused SDK packages don't affect startup time.

Supported values for EMBEDDING_PROVIDER:
  ollama  →  OllamaEmbeddingProvider  (local, free — needs nomic-embed-text model)
  titan   →  TitanEmbeddingProvider   (AWS Bedrock — needs IAM permissions)
"""

import os

from .embedding import EmbeddingProvider

_instance: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return a cached embedding provider instance."""
    global _instance
    if _instance is not None:
        return _instance

    provider_name = os.getenv("EMBEDDING_PROVIDER", "").lower().strip()

    if provider_name == "ollama":
        from .embedding import OllamaEmbeddingProvider
        _instance = OllamaEmbeddingProvider()

    elif provider_name == "titan":
        from .embedding import TitanEmbeddingProvider
        _instance = TitanEmbeddingProvider()

    elif not provider_name:
        raise ValueError(
            "EMBEDDING_PROVIDER is not set. "
            "Supported values: ollama | titan"
        )
    else:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER='{provider_name}'. "
            "Supported values: ollama | titan"
        )

    return _instance


def reset_embedding_provider() -> None:
    """Clear the cached provider (useful in tests)."""
    global _instance
    _instance = None
