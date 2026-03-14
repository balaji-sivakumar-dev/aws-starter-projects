# Architecture — Template 3 Containerised Journal

## AWS Architecture Diagram

![Reflect App AWS Architecture](Reflect%20APP%20AWS.drawio.png)

> Source: [`Reflect APP AWS.drawio.xml`](Reflect%20APP%20AWS.drawio.xml) — open in [draw.io](https://app.diagrams.net) to edit. Update this diagram whenever new AWS services are added.

---

## Overview

Full-stack journal app with AI enrichment. Runs entirely as Docker containers locally; deploys to AWS without changing business logic.

```
Browser → Nginx (port 3000)
            ├── /          → React SPA (static)
            └── /api/*     → FastAPI (port 8080)
                               └── DynamoDB
                                     (local: amazon/dynamodb-local)
                                     (AWS:   DynamoDB on-demand)
```

---

## Tech stack

| Layer | Local | AWS target |
|-------|-------|------------|
| Web   | React + Vite, served by Nginx container | S3 + CloudFront |
| API   | Python FastAPI, uvicorn | ECS/Fargate **or** Lambda |
| DB    | `amazon/dynamodb-local` (in-memory) | DynamoDB on-demand |
| Auth  | `X-User-Id` header bypass | Cognito PKCE (RS256 JWT) |
| AI    | Ollama / Groq / OpenAI — swappable via `LLM_PROVIDER` | Bedrock / Step Functions (Phase 5) |

---

## API — core + adapters pattern

Business logic lives in `services/api/src/core/` with no framework dependencies. Adapters wire it to the chosen runtime.

```
src/
├── core/
│   ├── handlers.py     ← all business logic (create/list/get/update/delete/trigger_ai)
│   ├── repository.py   ← DynamoDB CRUD
│   ├── auth.py         ← JWT validation + local bypass
│   └── models.py       ← Pydantic models, AppError
├── adapters/
│   ├── fastapi/        ← routes, deps, app factory  (container / local)
│   └── lambda_/        ← direct Lambda handler       (serverless, no FastAPI overhead)
├── llm/
│   ├── interface.py    ← LLMProvider ABC
│   ├── factory.py      ← reads LLM_PROVIDER env var, caches provider instance
│   └── providers/      ← ollama_provider, groq_provider, openai_provider
├── main.py             ← uvicorn entrypoint (Docker / ECS)
├── lambda_mangum.py    ← Mangum wrapper  (Lambda container with full FastAPI)
└── lambda_handler.py   ← direct handler  (Lambda zip, minimal cold start)
```

### API deployment modes

| Mode | Entrypoint | When to use |
|------|-----------|-------------|
| Docker / ECS | `src.main:app` (uvicorn) | Local dev, ECS/Fargate |
| Lambda + Mangum | `src.lambda_mangum.handler` | Lambda container — full FastAPI stack |
| Lambda direct | `src.lambda_handler.handler` | Lambda zip — minimal cold start |

---

## API contract

Auth: `X-User-Id: <id>` header in local mode; `Authorization: Bearer <jwt>` in AWS mode.

**Journal entries**

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/health` | Health check (no auth) |
| GET    | `/me` | Resolved user identity |
| GET    | `/entries` | List entries (`?limit=&nextToken=`) |
| POST   | `/entries` | Create entry |
| GET    | `/entries/{id}` | Get single entry |
| PUT    | `/entries/{id}` | Update title/body |
| DELETE | `/entries/{id}` | Soft delete |
| POST   | `/entries/{id}/ai` | Trigger AI enrichment (async via Step Functions on AWS) |

**Insights (period summaries)**

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/insights/summaries` | List summaries for the user |
| POST   | `/insights/summaries` | Generate a new period summary (weekly / monthly / yearly) |
| GET    | `/insights/summaries/{id}` | Get a single summary |
| DELETE | `/insights/summaries/{id}` | Delete a summary |
| POST   | `/insights/summaries/{id}/regenerate` | Regenerate an existing summary |

Error shape: `{ "code": string, "message": string }` + HTTP status code.

---

## DynamoDB data model (single-table)

| Item type | PK | SK |
|-----------|----|----|
| Journal entry | `USER#<userId>` | `ENTRY#<createdAt>#<entryId>` |
| Entry lookup  | `USER#<userId>` | `ENTRYID#<entryId>` |
| Period summary | `USER#<userId>` | `PERIOD_SUMMARY#<createdAt>#<summaryId>` |

The lookup item lets `GET /entries/{id}` resolve without knowing `createdAt`. Deleted entries are soft-deleted (`deletedAt` timestamp set).

**Period summary fields:** `summaryId`, `period` (weekly/monthly/yearly), `startDate`, `endDate`, `entryCount`, `narrative`, `themes` (list), `mood`, `aiStatus` (QUEUED / DONE / ERROR / NOT_CONFIGURED), `createdAt`.

**GSI:** `userId-createdAt-index` on `userId` + `createdAt` — used by the AI Lambda to fetch entries in a date range for period summary generation.

---

## AI enrichment

### Local mode (Docker)

`POST /entries/{id}/ai` calls the configured LLM provider **synchronously** and writes `summary`, `tags`, and `aiStatus` back to DynamoDB.

Provider is selected by `LLM_PROVIDER` env var — no code changes needed to switch:

| `LLM_PROVIDER` | Env vars needed | Notes |
|----------------|----------------|-------|
| `ollama` | `OLLAMA_HOST`, `OLLAMA_MODEL` | Free, runs locally |
| `groq` | `GROQ_API_KEY` | Free cloud tier, fast |
| `openai` | `OPENAI_API_KEY` | Also works with compatible endpoints via `OPENAI_BASE_URL` |
| _(unset)_ | — | Returns `aiStatus: SKIPPED` stub |

### AWS mode (Step Functions + AI Gateway Lambda)

On AWS, AI enrichment is **asynchronous** via Step Functions:

```
API Lambda
  └── POST /entries/{id}/ai  → sets aiStatus=QUEUED → starts Step Functions execution
  └── POST /insights/summaries → sets aiStatus=QUEUED → starts Step Functions execution

Step Functions state machine (process_entry_ai.asl.json)
  └── ValidateInput (Choice)
        ├── entryId present  → InvokeAIGateway → enrich_entry
        └── summaryId present → InvokeAIGateway → generate_summary

AI Gateway Lambda (ai_gateway.py)
  ├── enrich_entry   → fetches entry → calls LLM → writes summary + tags + aiStatus=DONE
  └── generate_summary → queries entries by date range → calls LLM → writes narrative + themes + mood
```

The Groq API key is stored in **SSM Parameter Store** (`/journal/<env>/groq_api_key`) and fetched at deploy time — never stored in tfvars or code.

---

## Auth modes

| `APP_ENV` | Auth behaviour |
|-----------|----------------|
| `local` / `test` | `X-User-Id` header → user ID; defaults to `dev-user` |
| anything else | `Authorization: Bearer <jwt>` → validated against Cognito JWKS (RS256) |

### Cognito user pool (AWS)

- **Flow:** Authorization Code + PKCE (no client secret)
- **Scopes:** `openid email profile`
- **Standard attributes collected at sign-up:** `email` (required), `given_name` (required)
- **Optional attributes:** `family_name`
- **id_token claims used by the frontend:** `email`, `given_name` — decoded client-side from `localStorage` without a separate JWKS call

### Frontend UI

The React app uses a **horizontal topnav** layout:
- **Left:** Reflect brand logo
- **Centre:** Home / Journal / Insights navigation tabs
- **Right:** user email pill + Sign out button

The Dashboard greeting uses `given_name` from the Cognito `id_token` if available; otherwise derives a first name from the email local-part (e.g. `john.doe@co.com` → `John`).
