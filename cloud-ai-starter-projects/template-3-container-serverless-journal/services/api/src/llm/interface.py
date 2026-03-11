"""
LLM Provider interface.

All providers implement this ABC so the rest of the codebase
never depends on a specific SDK. Swap providers by changing
the LLM_PROVIDER environment variable — no code changes needed.

LLM_PROVIDER values:
  ollama  →  local Ollama server  (default model: llama3.2)
  groq    →  Groq cloud API       (fast inference, generous free tier)
  openai  →  OpenAI API           (GPT-4o / GPT-4o-mini)

Usage:
    from src.llm.factory import get_provider
    provider = get_provider()
    result = provider.enrich(title="My entry", body="Today I felt...")
    # result → {"summary": "...", "tags": ["reflection", ...]}
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        """
        Generate a summary and tags for a journal entry.

        Args:
            title: Entry title.
            body:  Entry body text.

        Returns:
            {"summary": str, "tags": List[str]}

        Raises:
            Exception on provider errors (caller handles retry / error state).
        """

    # ── Shared prompt helpers ─────────────────────────────────────────────────

    @staticmethod
    def build_prompt(title: str, body: str) -> str:
        return (
            "You are a journaling assistant. Analyse the journal entry below "
            "and respond with valid JSON only — no markdown, no commentary.\n\n"
            f"Title: {title}\n\n"
            f"Body:\n{body}\n\n"
            "Respond with exactly this JSON shape:\n"
            '{"summary": "<2-3 sentence summary>", "tags": ["<tag1>", "<tag2>", ...]}\n'
            "Tags should be lowercase, single-word or hyphenated, max 5 tags."
        )

    @staticmethod
    def parse_response(raw: str) -> Dict[str, Any]:
        """
        Parse the LLM JSON response. Falls back gracefully if the model
        doesn't return perfectly structured output.
        """
        import json
        import re

        # Strip markdown code fences if present
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()

        try:
            data = json.loads(clean)
            return {
                "summary": str(data.get("summary") or "").strip(),
                "tags": [str(t).lower().strip() for t in data.get("tags", []) if t][:5],
            }
        except json.JSONDecodeError:
            # Best-effort fallback
            return {"summary": clean[:500], "tags": []}
