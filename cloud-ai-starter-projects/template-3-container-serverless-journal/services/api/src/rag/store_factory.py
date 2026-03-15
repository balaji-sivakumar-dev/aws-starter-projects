"""
Vector store factory.

Reads VECTOR_STORE from the environment and returns the appropriate store.

Supported values:
  chroma  →  ChromaDBStore  (local Docker container)
"""

import os

from .store import VectorStore

_instance: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Return a cached vector store instance."""
    global _instance
    if _instance is not None:
        return _instance

    store_name = os.getenv("VECTOR_STORE", "").lower().strip()

    if store_name == "chroma":
        from .store import ChromaDBStore
        _instance = ChromaDBStore()

    elif not store_name:
        raise ValueError(
            "VECTOR_STORE is not set. "
            "Supported values: chroma"
        )
    else:
        raise ValueError(
            f"Unknown VECTOR_STORE='{store_name}'. "
            "Supported values: chroma"
        )

    return _instance


def reset_vector_store() -> None:
    """Clear the cached store (useful in tests)."""
    global _instance
    _instance = None
