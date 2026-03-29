# Template 3 — Reflect Journal App — Claude Instructions

Project-specific rules for the Reflect journal app (Template 3).
Inherits all rules from `../template/CLAUDE.md` (base template rules).
Global rules in `~/.claude/CLAUDE.md` also apply.

---

## Project Context

**Reflect** is an AI-powered journal app demonstrating:
- Container (ECS Fargate) + Serverless (Lambda) hybrid architecture
- RAG pipeline using DynamoDB vector store + Bedrock Titan Embeddings V2 (1024-dim)
- Cognito auth with PKCE, Admin dashboard, Audit logging
- AI enrichment via Step Functions + Bedrock Nova Lite / Groq

Key directories:
- `services/api/` — FastAPI backend (core + adapters pattern)
- `services/lambda_api/` — Lambda handler wrapper
- `services/workflows/` — Step Functions + AI Gateway Lambda
- `apps/web/` — React SPA (Vite, JSX)
- `infra/terraform/` — All infrastructure (8 modules)
- `scripts/setup/` — Numbered deployment scripts
- `scripts/seed_data/` — Seed scripts (run via `seed_data.py`)
- `docs/` — Architecture, Setup, draw.io diagram

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

## Reflect-Specific Rules

### App Configuration
- `APP_PREFIX` = `journal` (Terraform variable, flows to all resource names)
- `AWS_REGION` = `ca-central-1`, `BEDROCK_REGION` = `us-east-1` (cross-region)
- Compute mode: `serverless` (Lambda handles all routes in production)

### DynamoDB Entity Prefixes
```
PK: USER#{userId}
SK: ENTRY#{createdAt}#{entryId}              — Journal entry
SK: ENTRYID#{entryId}                        — Entry lookup by ID
SK: PERIOD_SUMMARY#{createdAt}#{summaryId}   — AI-generated period summary
SK: VECTOR#{entryId}                         — RAG embedding (1024-dim)
SK: CONVERSATION#{conversationId}            — RAG chat history
SK: AUDIT#{timestamp}#{action}               — Admin audit log
SK: RATE#{windowKey}                         — Rate limiter counter
```

### AI Provider Selection
- Default: Bedrock Nova Lite (no API key needed, IAM auth)
- Optional: Groq (requires API key in SSM)
- `providerOverride` passed in Step Functions input selects at runtime
- `X-LLM-Provider` header allows per-request override from frontend

### SSM Parameters
```
/journal/{env}/cognito/allowed_emails   — read live by pre-signup Lambda (no redeploy)
/journal/{env}/cognito/admin_emails     — baked into Lambda env var (requires make deploy-backend)
/journal/{env}/ai/groq_api_key          — read by AI Gateway Lambda at invocation
```

### Admin Management
| Action | Steps | Redeploy? |
|---|---|---|
| Add new user | `.env.users` → `make secrets` | No — pre-signup Lambda reads SSM live |
| Add/change admin | `.env.users` → `make secrets` → `make deploy-backend` | Yes — ADMIN_EMAILS is Lambda env var |

---

## Implementation Checklist

See `IMPLEMENTATION_CHECKLIST.md` in this directory for all tracked items.
