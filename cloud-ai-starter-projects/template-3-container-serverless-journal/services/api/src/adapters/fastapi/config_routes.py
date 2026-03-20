"""
Config endpoints — runtime configuration visible to the frontend.

Endpoints:
  GET /config/providers   list available (configured) LLM providers
"""

from fastapi import APIRouter

from ...llm.factory import available_providers, default_provider_name

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/providers")
def list_providers():
    """Return the list of LLM providers that have their API keys configured."""
    providers = available_providers()
    default = default_provider_name()
    return {
        "providers": providers,
        "default": default,
    }
