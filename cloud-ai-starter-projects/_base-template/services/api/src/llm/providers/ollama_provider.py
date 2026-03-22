"""
Ollama provider — runs models locally via the Ollama server.

Prerequisites:
  1. Install Ollama: https://ollama.com/download
  2. Pull a model:   ollama pull llama3.2
  3. Start server:   ollama serve   (or it auto-starts on macOS/Linux)

In Docker Compose, add the ollama service to docker-compose.yml and set:
  LLM_PROVIDER=ollama
  OLLAMA_HOST=http://ollama:11434
  OLLAMA_MODEL=llama3.2
"""

import logging
import os
from typing import Any, Dict, List

from ..interface import LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama3.2"
DEFAULT_HOST = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        import ollama  # lazy import

        self.model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        host = os.getenv("OLLAMA_HOST", DEFAULT_HOST)
        self.client = ollama.Client(host=host)
        logger.info("OllamaProvider initialised (host=%s, model=%s)", host, self.model)

    def _chat(self, prompt: str) -> str:
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3},
        )
        raw = response["message"]["content"]
        logger.debug("Ollama raw response: %s", raw)
        return raw

    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        logger.info("Ollama enrich: model=%s", self.model)
        return self.parse_response(self._chat(self.build_prompt(title, body)))

    def analyze_period(self, entries: List[Dict[str, Any]], period_label: str) -> Dict[str, Any]:
        logger.info("Ollama analyze_period: model=%s period=%s entries=%d", self.model, period_label, len(entries))
        return self.parse_period_response(self._chat(self.build_period_prompt(entries, period_label)))
