# Template 3 — Reflect Journal App — Claude Preferences

Project-specific rules for the Reflect journal app (Template 3).
Global rules in `~/.claude/CLAUDE.md` and repo rules in `../../CLAUDE.md` also apply.

---

## Project Context

**Reflect** is an AI-powered journal app demonstrating:
- Container (ECS Fargate) + Serverless (Lambda) hybrid architecture
- RAG pipeline using ChromaDB + Ollama (local) or Bedrock (AWS)
- Cognito auth, Admin dashboard, Audit logging

Key directories:
- `services/api/` — FastAPI backend
- `apps/web/` — React frontend (Vite)
- `scripts/seed_data/` — seed scripts (run via `seed_data.py`)
- `docs/` — all documentation

---

## Docker Compose Stack

Always use the overlay pattern when starting the full RAG stack:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.ollama.yml \
  -f docker-compose.rag.yml \
  up -d
```

ChromaDB image is pinned to `0.6.3` to match the Python client (`chromadb==0.6.3`).
Do NOT bump either version independently — they must stay in sync.

---

## Implementation Rules

<!-- Add template-specific coding conventions, API patterns, naming rules here -->
<!-- Examples: FastAPI endpoint patterns, React state patterns, test fixtures -->

---

## Implementation Checklist

See `IMPLEMENTATION_CHECKLIST.md` at this directory for all tracked items.
