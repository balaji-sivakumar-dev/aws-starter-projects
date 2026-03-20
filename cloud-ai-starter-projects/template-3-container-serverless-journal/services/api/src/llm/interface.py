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
from typing import Any, Dict, List  # noqa: F401 — List re-exported for providers


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        """
        Generate a summary and tags for a single journal entry.

        Returns:
            {"summary": str, "tags": List[str]}
        """

    @abstractmethod
    def analyze_period(self, entries: List[Dict[str, Any]], period_label: str) -> Dict[str, Any]:
        """
        Analyze a set of journal entries for a time period and return insights.

        Args:
            entries:      List of entry dicts (keys: title, body, createdAt, tags, summary).
            period_label: Human-readable period name, e.g. "March 2026" or "Week 10, 2026".

        Returns:
            {
                "narrative":  str,        # 2-3 paragraph synthesis of the period
                "themes":     List[str],  # recurring themes (max 6, lowercase)
                "mood":       str,        # overall mood/tone
                "highlights": List[str],  # up to 3 notable moments/entries
                "reflection": str,        # one forward-looking question or insight
            }
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
    def build_period_prompt(entries: List[Dict[str, Any]], period_label: str) -> str:
        lines = [
            "You are a journaling assistant. Analyse the journal entries below "
            f'for the period "{period_label}" and respond with valid JSON only '
            "— no markdown, no commentary.\n",
        ]
        for i, e in enumerate(entries[:30], 1):  # cap at 30 to stay within context
            lines.append(f"Entry {i} ({e.get('createdAt', '')[:10]}): {e['title']}")
            lines.append(e["body"][:400])  # truncate very long bodies
            lines.append("")

        lines.append(
            "Respond with exactly this JSON shape:\n"
            "{\n"
            '  "narrative": "<2-3 paragraph synthesis of the period>",\n'
            '  "themes": ["<theme1>", ...],\n'
            '  "mood": "<overall mood/tone in 2-4 words>",\n'
            '  "highlights": ["<notable moment or entry title>", ...],\n'
            '  "reflection": "<one forward-looking question or insight>"\n'
            "}\n"
            "themes: lowercase, max 6. highlights: max 3 items."
        )
        return "\n".join(lines)

    @staticmethod
    def _extract_json(raw: str) -> str:
        """
        Strip markdown fences and extract the first complete JSON object from the
        LLM response. LLMs sometimes prepend/append prose around the JSON block;
        this handles that gracefully.
        """
        import re

        # Remove markdown code fences (```json … ``` or ``` … ```)
        clean = re.sub(r"```(?:json)?", "", raw)
        clean = re.sub(r"```", "", clean).strip()

        # Find the outermost {...} block
        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            return clean[start : end + 1]
        return clean

    @staticmethod
    def parse_response(raw: str) -> Dict[str, Any]:
        """Parse a per-entry enrich() response, with fallback."""
        import json

        json_str = LLMProvider._extract_json(raw)
        try:
            data = json.loads(json_str)
            return {
                "summary": str(data.get("summary") or "").strip(),
                "tags": [str(t).lower().strip() for t in data.get("tags", []) if t][:5],
            }
        except (json.JSONDecodeError, ValueError):
            return {"summary": json_str[:500], "tags": []}

    @staticmethod
    def parse_period_response(raw: str) -> Dict[str, Any]:
        """Parse an analyze_period() response, with fallback."""
        import json

        json_str = LLMProvider._extract_json(raw)
        try:
            data = json.loads(json_str)
            return {
                "narrative": str(data.get("narrative") or "").strip(),
                "themes": [str(t).lower().strip() for t in data.get("themes", []) if t][:6],
                "mood": str(data.get("mood") or "").strip(),
                "highlights": [str(h).strip() for h in data.get("highlights", []) if h][:3],
                "reflection": str(data.get("reflection") or "").strip(),
            }
        except (json.JSONDecodeError, ValueError):
            return {
                "narrative": json_str[:1000],
                "themes": [],
                "mood": "",
                "highlights": [],
                "reflection": "",
            }
