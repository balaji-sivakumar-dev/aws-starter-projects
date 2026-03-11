# Template 3 — Implementation Plan

> Tracks all work items as GitHub-style issues. Mark `[x]` when done. Add new items at the bottom of each section.

---

## Phase 1 — Local Docker Setup

### #1 — Python FastAPI service
- [x] `services/api/src/main.py` — FastAPI app, CORS, lifespan (table auto-create locally)
- [x] `services/api/src/auth.py` — Dual-mode auth: `X-User-Id` header (local) / Cognito JWT (AWS)
- [x] `services/api/src/repository.py` — DynamoDB CRUD (boto3), configurable endpoint
- [x] `services/api/src/models.py` — Pydantic request/response models
- [x] `services/api/src/routes.py` — All REST endpoints (health, me, entries CRUD, /ai stub)
- [x] `services/api/requirements.txt`
- [x] `services/api/Dockerfile`

### #2 — React web container
- [x] `apps/web/src/config.js` — Add `authMode` + `localUserId`; skip Cognito check in local mode
- [x] `apps/web/src/auth/auth.js` — Local mode bypass (`isAuthed` always true, no Cognito redirects)
- [x] `apps/web/src/api/client.js` — Send `X-User-Id` header in local mode instead of Bearer token
- [x] `apps/web/Dockerfile` — Multi-stage: Node build → Nginx serve
- [x] `apps/web/nginx.conf` — SPA routing + `/api/` proxy to api service

### #3 — Docker Compose
- [x] `docker-compose.yml` — Wires: dynamodb-local + api + web
- [x] `.env.docker` — Example env file for local Docker run

---

## Phase 2 — Local Testing & Validation

### #4 — Smoke tests
- [ ] `docker compose up --build` completes without errors
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `GET /me` returns `{"userId": "dev-user"}` (local auth bypass)
- [ ] Create, list, get, update, delete a journal entry end-to-end
- [ ] React UI loads at `http://localhost:3000` and can perform all CRUD ops

### #5 — Integration tests (pytest)
- [ ] `services/api/tests/test_entries.py` — CRUD happy path against dynamodb-local
- [ ] `services/api/tests/test_auth.py` — Local bypass + bad token (400/401 cases)
- [ ] `services/api/tests/conftest.py` — Pytest fixtures: spin up test DDB table

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

## Phase 4 — AI Workflow (future)

### #11 — Step Functions AI pipeline
- [ ] Define ASL state machine (already started in `statemachine/`)
- [ ] Wire `POST /entries/{id}/ai` to start Step Functions execution
- [ ] AI gateway: call Bedrock for summary + tag generation
- [ ] Write AI results back to DynamoDB (`aiStatus`, `summary`, `tags`)
- [ ] Local simulation: replace Step Functions with a direct Python function call (dev mode)

---

## Enhancements / Bugs

> Add new items here as they come up.

- [ ] Add pagination UI controls to React entry list
- [ ] Add loading skeleton / spinner to entry detail
- [ ] Health check endpoint should include DynamoDB connectivity status
- [ ] API error responses should be consistent JSON `{code, message, requestId}`
