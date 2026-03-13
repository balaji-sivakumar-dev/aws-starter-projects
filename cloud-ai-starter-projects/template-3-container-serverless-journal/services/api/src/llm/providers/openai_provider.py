"""
OpenAI provider — GPT-4o / GPT-4o-mini via the OpenAI API.

Also compatible with any OpenAI-compatible API endpoint
(Azure OpenAI, Together AI, Perplexity, etc.) via OPENAI_BASE_URL.

Setup:
  1. Get an API key from https://platform.openai.com
  2. Set env vars:
       LLM_PROVIDER=openai
       OPENAI_API_KEY=sk-...
       OPENAI_MODEL=gpt-4o-mini          (optional, default is gpt-4o-mini)
       OPENAI_BASE_URL=https://...       (optional, for compatible endpoints)
"""

import logging
import os
from typing import Any, Dict, List, Optional

from ..interface import LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        from openai import OpenAI  # lazy import

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")

        base_url: Optional[str] = os.getenv("OPENAI_BASE_URL") or None
        self.model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(
            "OpenAIProvider initialised (model=%s, base_url=%s)",
            self.model,
            base_url or "default",
        )

    def _complete(self, prompt: str, max_tokens: int = 512) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        raw = completion.choices[0].message.content or ""
        logger.debug("OpenAI raw response: %s", raw)
        return raw

    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        logger.info("OpenAI enrich: model=%s", self.model)
        return self.parse_response(self._complete(self.build_prompt(title, body)))

    def analyze_period(self, entries: List[Dict[str, Any]], period_label: str) -> Dict[str, Any]:
        logger.info("OpenAI analyze_period: model=%s period=%s entries=%d", self.model, period_label, len(entries))
        return self.parse_period_response(
            self._complete(self.build_period_prompt(entries, period_label), max_tokens=1024)
        )
