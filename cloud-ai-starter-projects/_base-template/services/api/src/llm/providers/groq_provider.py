"""
Groq provider — fast cloud inference via the Groq API.

Groq offers a generous free tier with very fast inference (LPU hardware).
Models available for free: llama-3.3-70b-versatile, mixtral-8x7b-32768, etc.

Setup:
  1. Sign up at https://console.groq.com  (free)
  2. Create an API key
  3. Set env vars:
       LLM_PROVIDER=groq
       GROQ_API_KEY=gsk_...
       GROQ_MODEL=llama-3.3-70b-versatile   (optional, this is the default)
"""

import logging
import os
from typing import Any, Dict, List

from ..interface import LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqProvider(LLMProvider):
    def __init__(self) -> None:
        from groq import Groq  # lazy import

        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required for Groq provider")

        self.model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
        self.client = Groq(api_key=api_key)
        logger.info("GroqProvider initialised (model=%s)", self.model)

    def _complete(self, prompt: str, max_tokens: int = 512) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        raw = completion.choices[0].message.content or ""
        logger.debug("Groq raw response: %s", raw)
        return raw

    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        logger.info("Groq enrich: model=%s", self.model)
        return self.parse_response(self._complete(self.build_prompt(title, body)))

    def analyze_period(self, entries: List[Dict[str, Any]], period_label: str) -> Dict[str, Any]:
        logger.info("Groq analyze_period: model=%s period=%s entries=%d", self.model, period_label, len(entries))
        return self.parse_period_response(
            self._complete(self.build_period_prompt(entries, period_label), max_tokens=1024)
        )
