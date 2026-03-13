# Architecture — Template 3 Containerised Journal

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

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/health` | Health check (no auth) |
| GET    | `/me` | Resolved user identity |
| GET    | `/entries` | List entries (`?limit=&nextToken=`) |
| POST   | `/entries` | Create entry |
| GET    | `/entries/{id}` | Get single entry |
| PUT    | `/entries/{id}` | Update title/body |
| DELETE | `/entries/{id}` | Soft delete |
| POST   | `/entries/{id}/ai` | Trigger AI enrichment (summary + tags) |

Error shape: `{ "code": string, "message": string }` + HTTP status code.

---

## DynamoDB data model (single-table)

| Item type | PK | SK |
|-----------|----|----|
| Journal entry | `USER#<userId>` | `ENTRY#<createdAt>#<entryId>` |
| Entry lookup  | `USER#<userId>` | `ENTRYID#<entryId>` |

The lookup item lets `GET /entries/{id}` resolve without knowing `createdAt`. Deleted entries are soft-deleted (`deletedAt` timestamp set).

---

## AI enrichment

`POST /entries/{id}/ai` calls the configured LLM provider synchronously and writes `summary`, `tags`, and `aiStatus` back to DynamoDB.

Provider is selected by `LLM_PROVIDER` env var — no code changes needed to switch:

| `LLM_PROVIDER` | Env vars needed | Notes |
|----------------|----------------|-------|
| `ollama` | `OLLAMA_HOST`, `OLLAMA_MODEL` | Free, runs locally |
| `groq` | `GROQ_API_KEY` | Free cloud tier, fast |
| `openai` | `OPENAI_API_KEY` | Also works with compatible endpoints via `OPENAI_BASE_URL` |
| _(unset)_ | — | Returns `aiStatus: SKIPPED` stub |

---

## Auth modes

| `APP_ENV` | Auth behaviour |
|-----------|----------------|
| `local` / `test` | `X-User-Id` header → user ID; defaults to `dev-user` |
| anything else | `Authorization: Bearer <jwt>` → validated against Cognito JWKS (RS256) |
