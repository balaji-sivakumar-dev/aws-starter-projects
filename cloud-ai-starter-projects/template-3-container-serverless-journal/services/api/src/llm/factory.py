"""
LLM provider factory.

Reads LLM_PROVIDER from the environment and returns the appropriate provider.
Providers are imported lazily so unused SDK packages don't affect startup time.

Supported values for LLM_PROVIDER:
  ollama  →  OllamaProvider  (local, free — needs `ollama serve`)
  groq    →  GroqProvider    (cloud, free tier — needs GROQ_API_KEY)
  openai  →  OpenAIProvider  (cloud, paid — needs OPENAI_API_KEY)

To add a new provider:
  1. Create providers/my_provider.py implementing LLMProvider
  2. Add a case in get_provider() below
  3. Document required env vars in the provider module
"""

import os

from .interface import LLMProvider

_instance: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """
    Return a cached LLM provider instance.
    Raises ValueError if LLM_PROVIDER is unset or unknown.
    """
    global _instance
    if _instance is not None:
        return _instance

    provider_name = os.getenv("LLM_PROVIDER", "").lower().strip()

    if provider_name == "ollama":
        from .providers.ollama_provider import OllamaProvider
        _instance = OllamaProvider()

    elif provider_name == "groq":
        from .providers.groq_provider import GroqProvider
        _instance = GroqProvider()

    elif provider_name == "openai":
        from .providers.openai_provider import OpenAIProvider
        _instance = OpenAIProvider()

    elif not provider_name:
        raise ValueError(
            "LLM_PROVIDER is not set. "
            "Supported values: ollama | groq | openai"
        )
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER='{provider_name}'. "
            "Supported values: ollama | groq | openai"
        )

    return _instance


def reset_provider() -> None:
    """Clear the cached provider (useful in tests to swap providers)."""
    global _instance
    _instance = None
