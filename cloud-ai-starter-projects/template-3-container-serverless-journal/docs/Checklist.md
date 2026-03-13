# Checklist — Template 3

> Tracks all work items as GitHub-style issues. Mark `[x]` when done. Add new items at the bottom of each section.

---

## Phase 1 — Local Docker Setup

### #1 — Python API — core + adapters (lambda-ready)
- [x] `src/core/models.py` — Pydantic models + `AppError` (framework-agnostic)
- [x] `src/core/repository.py` — DynamoDB CRUD, configurable endpoint, table auto-create
- [x] `src/core/auth.py` — Pure JWT/local auth logic (no FastAPI deps)
- [x] `src/core/handlers.py` — All business logic; called by both adapters
- [x] `src/adapters/fastapi/app.py` — FastAPI app, CORS, lifespan
- [x] `src/adapters/fastapi/deps.py` — FastAPI `Depends` auth wrapper
- [x] `src/adapters/fastapi/routes.py` — Thin routes → core handlers
- [x] `src/adapters/lambda_/handler.py` — Direct Lambda adapter (no FastAPI)
- [x] `src/main.py` — uvicorn entrypoint (container deployment)
- [x] `src/lambda_handler.py` — Lambda direct entrypoint
- [x] `src/lambda_mangum.py` — Lambda+Mangum entrypoint (full FastAPI in Lambda)
- [x] `requirements.txt` + `requirements-lambda.txt` (adds `mangum`)
- [x] `Dockerfile`

### #2 — React web container
- [x] `apps/web/src/config.js` — Add `authMode` + `localUserId`; skip Cognito check in local mode
- [x] `apps/web/src/auth/auth.js` — Local mode bypass (`isAuthed` always true, no Cognito redirects)
- [x] `apps/web/src/api/client.js` — Send `X-User-Id` header in local mode instead of Bearer token
- [x] `apps/web/Dockerfile` — Multi-stage: Node build → Nginx serve
- [x] `apps/web/nginx.conf` — SPA routing + `/api/` proxy to api service

### #3 — Docker Compose + docs
- [x] `docker-compose.yml` — Wires: dynamodb-local + api + web (health-check gated)
- [x] `.env.docker` — Example env file for local Docker run
- [x] `local-setup.md` — Full local setup guide (Docker, API calls, LLM, DynamoDB inspection)
- [x] `README.md` — Updated with quick start, architecture table, deployment modes

---

## Phase 2 — Local Testing & Validation

### #4 — Smoke tests
- [x] `docker compose up --build` completes without errors
- [x] `GET /health` returns `{"status": "ok"}`
- [x] `GET /me` returns `{"userId": "dev-user"}` (local auth bypass)
- [x] Create, list, get, update, delete a journal entry end-to-end
- [x] React UI loads at `http://localhost:3000` and Nginx `/api/` proxy works

### #5 — Integration tests (pytest)
- [x] `services/api/tests/test_entries.py` — CRUD happy path (28 tests, moto mock, 1.6s)
- [x] `services/api/tests/test_auth.py` — Local bypass + user isolation + 400/401/404 cases
- [x] `services/api/tests/conftest.py` — moto `mock_aws` fixture; table created before TestClient
- [x] `services/api/requirements-dev.txt` — pytest + moto[dynamodb]

---

## Phase 3 — AWS Deployment

### #6 — Terraform: ECS/Fargate for API
- [ ] ECR repository for API image
- [ ] ECS cluster + Fargate task definition
- [ ] ALB + target group wiring
- [ ] IAM role for ECS task (DynamoDB access)
- [ ] Update `infra/terraform/modules/compute_container/` to use the new Python image

### #7 — Terraform: Cognito + real auth
- [ ] Cognito User Pool + App Client (PKCE)
- [ ] Wire Cognito issuer into ECS task env vars
- [ ] React build with `VITE_AUTH_MODE=cognito` and real Cognito domain

### #8 — Terraform: DynamoDB (prod)
- [ ] On-demand table with PK/SK key schema (matches local schema)
- [ ] Point-in-time recovery enabled

### #9 — Terraform: Web hosting (S3 + CloudFront)
- [ ] Build React with `VITE_API_BASE_URL=https://<alb-url>`
- [ ] Deploy to S3, serve via CloudFront

### #10 — AWS end-to-end validation
- [ ] Deploy with `terraform apply`
- [ ] Sign in via Cognito Hosted UI
- [ ] Create/list/edit/delete entries against real DynamoDB
- [ ] Confirm CloudFront → S3 web delivery

---

## Phase 3 — LLM Testing (local → cloud)

> Goal: validate the full AI enrichment loop (summary + tags) before wiring Step Functions.
> Provider is swappable via `LLM_PROVIDER` env var — no code changes needed.

### #11 — LLM interface + providers (scaffold ✅)
- [x] `src/llm/interface.py` — Abstract `LLMProvider` ABC + shared prompt helpers
- [x] `src/llm/factory.py` — Provider factory (reads `LLM_PROVIDER` env var, caches instance)
- [x] `src/llm/providers/ollama_provider.py` — Ollama (local, free)
- [x] `src/llm/providers/groq_provider.py` — Groq (cloud, generous free tier)
- [x] `src/llm/providers/openai_provider.py` — OpenAI (+ any compatible endpoint)
- [x] `src/core/handlers.py#trigger_ai` — Synchronous AI call wired to LLM factory

### #12 — Ollama local testing
- [x] Added `docker-compose.llm.yml` overlay: `ollama` + `ollama-pull` (auto-downloads `llama3.2`) + api env wiring
- [x] Model auto-pulled on first startup via `ollama-pull` one-shot container; cached in `ollama-data` volume
- [x] `LLM_PROVIDER=ollama`, `OLLAMA_HOST=http://ollama:11434` wired in overlay
- [x] `POST /entries/{id}/ai` end-to-end verified: `summary` + `tags` written to DynamoDB (`aiStatus=DONE`)

### #13 — Groq cloud testing
- [ ] Obtain free Groq API key from https://console.groq.com
- [ ] Set `LLM_PROVIDER=groq`, `GROQ_API_KEY=gsk_...` in docker-compose.yml api env
- [ ] Test same entry — compare output quality vs Ollama
- [ ] Check Groq rate limits on free tier (6k RPM for LLaMA 3.3 70B)

### #14 — Provider switch validation
- [ ] Confirm switching `LLM_PROVIDER` from `ollama` → `groq` → `openai` requires only env change
- [ ] Test with a large entry body (>500 words) — verify truncation / token limits handled
- [ ] Test error handling: invalid API key, model not found, network timeout

### #15 — LLM integration tests (pytest)
- [x] `tests/test_llm.py` — stub provider via `factory._instance` injection (9 tests, 0.65s)
- [x] Happy path: `aiStatus=DONE`, `summary`/`tags` persisted in DynamoDB
- [x] Error path: provider raises → `aiStatus=ERROR`, `aiError` populated, 502 returned
- [x] SKIPPED path: no `LLM_PROVIDER` → 202 with `aiStatus=SKIPPED`
- [x] User isolation: cannot enrich another user's entry → 404

---

## Phase 4 — AWS Deployment

### #16 — Terraform: ECS/Fargate for API
- [ ] ECR repository for API image
- [ ] ECS cluster + Fargate task definition
- [ ] ALB + target group wiring
- [ ] IAM role for ECS task (DynamoDB access)
- [ ] Update `infra/terraform/modules/compute_container/` to use the Python image

### #17 — Terraform: Cognito + real auth
- [ ] Cognito User Pool + App Client (PKCE)
- [ ] Wire Cognito issuer into ECS task env vars
- [ ] React build with `VITE_AUTH_MODE=cognito` and real Cognito domain

### #18 — Terraform: DynamoDB (prod)
- [ ] On-demand table with PK/SK key schema (matches local schema)
- [ ] Point-in-time recovery enabled

### #19 — Terraform: Web hosting (S3 + CloudFront)
- [ ] Build React with `VITE_API_BASE_URL=https://<alb-url>`
- [ ] Deploy to S3, serve via CloudFront

### #20 — AWS end-to-end validation
- [ ] Deploy with `terraform apply`
- [ ] Sign in via Cognito Hosted UI
- [ ] Create/list/edit/delete entries against real DynamoDB
- [ ] Trigger AI enrichment via `POST /entries/{id}/ai` on AWS

---

## Phase 5 — Async AI Workflow (Step Functions)

### #21 — Step Functions pipeline
- [ ] Define ASL state machine (started in `statemachine/`)
- [ ] Wire `POST /entries/{id}/ai` to start Step Functions execution (async)
- [ ] AI Lambda: calls LLM provider → writes results to DynamoDB
- [ ] Swap `LLM_PROVIDER=bedrock` for AWS-native option
- [ ] Local simulation: `LLM_PROVIDER=ollama` still works in direct-call mode

---

## Enhancements / Bugs

> Add new items here as they come up.

- [x] Switch DynamoDB Local to `-inMemory` mode — avoids SQLite volume permission issue (table auto-created on startup)
- [x] Add boto3 timeout config (`Config(connect_timeout=5, read_timeout=10, max_attempts=1)`) to `repository._resource()`
- [x] Rewrite `ensure_table()` to use `create_table()` + `ResourceInUseException` catch (skips slow `DescribeTable`); added retry loop for DynamoDB warm-up race
- [x] Add Ollama service to docker-compose.llm.yml for zero-config local LLM
- [ ] Add pagination UI controls to React entry list
- [ ] Add loading skeleton / spinner to entry detail
- [ ] Health check endpoint should report DynamoDB connectivity
- [ ] Add `GET /entries/{id}` polling to React UI to detect when `aiStatus=DONE`
