"""
LLM provider factory.

Supports multiple simultaneous providers cached by name.
The default provider is read from LLM_PROVIDER env var, but callers
can request a specific provider by name via get_provider(name).

Supported provider names:
  bedrock →  BedrockProvider (AWS, IAM-only — no API key, default for Lambda)
  ollama  →  OllamaProvider  (local, free — needs `ollama serve`)
  groq    →  GroqProvider    (cloud, free tier — needs GROQ_API_KEY)
  openai  →  OpenAIProvider  (cloud, paid — needs OPENAI_API_KEY)

To add a new provider:
  1. Create providers/my_provider.py implementing LLMProvider
  2. Add a case in _create_provider() below
  3. Add the name to KNOWN_PROVIDERS
  4. Document required env vars in the provider module
"""

import logging
import os
from typing import Dict, List, Optional

from .interface import LLMProvider

logger = logging.getLogger(__name__)

_cache: Dict[str, LLMProvider] = {}

# All recognised provider names and the env var that must be set for each.
KNOWN_PROVIDERS: Dict[str, Dict[str, str]] = {
    "bedrock": {
        "label": "AWS Bedrock",
        "env_key": "",  # IAM-only — no API key; requires AWS credentials in environment
        "default_model": "amazon.nova-lite-v1:0",
    },
    "ollama": {
        "label": "Ollama (local)",
        "env_key": "",  # no API key needed — just needs server running
        "default_model": "llama3.2",
    },
    "groq": {
        "label": "Groq",
        "env_key": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openai": {
        "label": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
    },
}


def _create_provider(name: str) -> LLMProvider:
    """Instantiate a provider by name. Raises ValueError on failure."""
    if name == "bedrock":
        from .providers.bedrock_provider import BedrockProvider
        return BedrockProvider()
    elif name == "ollama":
        from .providers.ollama_provider import OllamaProvider
        return OllamaProvider()
    elif name == "groq":
        from .providers.groq_provider import GroqProvider
        return GroqProvider()
    elif name == "openai":
        from .providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    else:
        raise ValueError(
            f"Unknown provider '{name}'. "
            f"Supported: {', '.join(KNOWN_PROVIDERS.keys())}"
        )


def get_provider(name: Optional[str] = None) -> LLMProvider:
    """
    Return a cached LLM provider instance.

    Args:
        name: Provider name (e.g. "groq", "openai"). If None, uses LLM_PROVIDER env var.

    Raises ValueError if no provider is configured.
    """
    if name is None:
        name = os.getenv("LLM_PROVIDER", "").lower().strip()
    else:
        name = name.lower().strip()

    if not name:
        raise ValueError(
            "LLM_PROVIDER is not set. "
            f"Supported values: {' | '.join(KNOWN_PROVIDERS.keys())}"
        )

    if name in _cache:
        return _cache[name]

    provider = _create_provider(name)
    _cache[name] = provider
    return provider


def available_providers() -> List[Dict[str, str]]:
    """
    Return a list of providers that are currently configured (API keys present).
    Used by the /config/providers endpoint.
    """
    result = []
    for name, info in KNOWN_PROVIDERS.items():
        env_key = info["env_key"]
        # Ollama has no API key — check if LLM_PROVIDER includes it or just always list it
        if env_key and not os.getenv(env_key):
            continue
        result.append({
            "name": name,
            "label": info["label"],
            "model": os.getenv(f"{name.upper()}_MODEL", info["default_model"]),
        })
    return result


def default_provider_name() -> str:
    """Return the default provider name from env, or empty string."""
    return os.getenv("LLM_PROVIDER", "").lower().strip()


def reset_provider() -> None:
    """Clear all cached providers (useful in tests)."""
    _cache.clear()
