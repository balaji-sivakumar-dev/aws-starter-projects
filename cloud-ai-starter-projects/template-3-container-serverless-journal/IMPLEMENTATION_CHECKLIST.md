# Implementation Checklist — Template 3 (Reflect)

Tracks all Requirements, Issues, and Fixes for the Reflect journal app.

**Status key:** `[ ]` open · `[~]` in progress · `[x]` complete (tested) · `[!]` blocked

---

## Requirements

| ID | Description | Status | Notes |
|---|---|---|---|
| REQ-001 | RAG pipeline — embed, search, ask journal | `[x]` | 20/20 integration tests passing locally |
| REQ-002 | Journal display — date/month filters + scroll | `[x]` | Year/month filters + scroll implemented |
| REQ-003 | Admin dashboard | `[x]` | Implemented |
| REQ-004 | Audit logging | `[x]` | Implemented |
| REQ-005 | Cognito auth | `[x]` | Implemented |

### Group A — AWS Deployment

| ID | Description | Status | Notes |
|---|---|---|---|
| REQ-006 | AWS Console Setup — manual steps not automatable via Terraform | `[x]` | `docs/AWS-Console-Setup.md` |
| REQ-007 | AWS Cost Estimate — monthly cost + what to keep vs shut down after testing | `[x]` | `docs/AWS-Cost-Estimate.md` |

### Group B — Security: User Access Control

| ID | Description | Status | Notes |
|---|---|---|---|
| REQ-008 | Cognito allowlist — pre-signup Lambda rejects unknown emails; list stored in SSM | `[x]` | `infra/terraform/modules/auth/lambda/pre_signup.py` + Terraform wiring + Step 1 in `docs/AWS-Console-Setup.md` |
| REQ-009 | Admin account setup — `GET /me` returns `isAdmin`; Admin tab hidden for non-admins | `[x]` | `core/handlers.py:me()` + `App.jsx` guard; Steps 2–3 in `docs/AWS-Console-Setup.md` |

### Group C — Rate Limiting

| ID | Description | Status | Notes |
|---|---|---|---|
| REQ-010 | Per-user daily rate limiting on `/rag/ask`, `/rag/embed-all`, `POST /insights/summaries` via DynamoDB atomic counter | `[x]` | `core/rate_limiter.py`; disabled in local/test mode; Step 7 in `docs/AWS-Console-Setup.md` |

---

### Group D — UI & UX Enhancements

| ID | Description | Status | Notes |
|---|---|---|---|
| REQ-011 | Mobile responsive UI — hamburger nav, stacked journal layout, touch-friendly targets | `[x]` | All pages: dashboard, journal, insights, ask, admin |
| REQ-012 | LLM provider selector — runtime dropdown to switch between Groq, OpenAI, Ollama | `[x]` | Backend multi-provider factory + `GET /config/providers` + frontend dropdown with `X-LLM-Provider` header |

### Group E — AWS Bedrock + Serverless RAG

| ID | Description | Status | Notes |
|---|---|---|---|
| REQ-013 | AWS Bedrock LLM provider — Claude/Nova via Converse API, IAM-only (no API key) | `[x]` | `services/api/src/llm/providers/bedrock_provider.py`; 6 unit tests passing |
| REQ-014 | DynamoDB vector store — serverless RAG without separate vector DB server | `[x]` | `services/api/src/rag/store.py` + `store_factory.py`; PK=`VEC#<tenant>` SK=`DOC#<doc>`; 9 unit tests passing |
| REQ-015 | Lambda-only deployment — remove ECS/Container/App Runner from setup docs | `[x]` | Setup docs focus on `compute_mode=serverless`; container mode still available via tfvar |

### Group F — Deployment & Ops

| ID | Description | Status | Notes |
|---|---|---|---|
| REQ-016 | .env.users for email allowlist — gitignored, picked up by `step-2b-store-secrets.sh` | `[x]` | `.env.users.example` exists; `.env.users` excluded from git |
| REQ-017 | AWS Console Setup doc — CLI commands moved to shell scripts; doc contains only console-only steps | `[x]` | `docs/AWS-Console-Setup.md` rewritten; `scripts/setup/step-2c-create-cognito-admin.sh` created |
| REQ-018 | AWS Console Setup doc — add Bedrock model access enablement steps (Nova Lite + Titan Embeddings V2) | `[x]` | Step 1 in `docs/AWS-Console-Setup.md`; required before first deploy |

---

## Issues

| ID | Description | Status | Notes |
|---|---|---|---|
| ISS-001 | ChromaDB healthcheck fails in Docker (`curl`/`python` not in container) | `[x]` | Fixed: use `bash /dev/tcp/localhost/8000` |
| ISS-002 | ChromaDB `KeyError: '_type'` — version mismatch between client and server | `[x]` | Fixed: pinned Docker image to `0.6.3` |
| ISS-003 | `/rag/ask` returns plain-text 500 instead of JSON | `[x]` | Fixed: added try/catch to all RAG endpoints |
| ISS-004 | Embed-all fails — `tuple indices must be integers or slices, not str` | `[x]` | Fixed + 11 unit tests passing |
| ISS-005 | Journal display has no scroll and no date/month filters | `[x]` | Year/month filters added, scroll intact |
| ISS-006 | Insights `POST /insights/summaries` 504 Gateway Timeout (HTML error) | `[x]` | Fixed: `nginx.conf` `proxy_read_timeout` 30s → 120s |
| ISS-007 | Embed-all `result["items"]` TypeError — `list_entries` returns tuple not dict | `[x]` | Fixed: `rag_routes.py` — unpack `(items, next_token)` tuple |
| ISS-008 | No integration tests for RAG and Insights against running local stack | `[x]` | `scripts/test_local_integration.sh` created |
| ISS-009 | Burger menu icons not rendering on mobile (nav icons missing) | `[ ]` | Low priority; UI only |
| ISS-010 | AWS-Console-Setup.md contains CLI commands that should be in shell scripts | `[x]` | Fixed: doc rewritten; `step-2c-create-cognito-admin.sh` handles Cognito user creation |
| ISS-011 | Seed script shows only 19–20 entries in UI — pagination limit was 20; seed docstring said "20 entries" | `[x]` | Fixed: `listEntries` limit 20→50; seed docstring updated to "~195 entries" |
| ISS-012 | Journal entries page lacks entry management — no total count, no bulk select, no delete-all | `[x]` | `GET /entries/count`, `POST /entries/bulk-delete`; EntryList manage mode with checkboxes + bulk delete; 8 new tests passing |
| ISS-013 | ASK conversations not stored or viewable — each `/rag/ask` call is stateless; no history shown in Ask section | `[x]` | `CONV#<ts>#<id>` entity in DynamoDB; `GET /rag/conversations`, `DELETE /rag/conversations/{id}`; AskJournal loads history on mount + clear-history UI; 8 tests passing |
| ISS-014 | Insights not filtering records by selected period — period selector UI exists but API may fetch all entries regardless of date range | `[x]` | Verified: `insights.py` computes start/end from period+year+week/month and passes to `get_entries_in_range`; frontend sends correct params. No bug. |

---

## Fixes

| ID | Description | Status | Related Issue |
|---|---|---|---|
| FIX-001 | ChromaDB healthcheck — switch to `bash /dev/tcp` | `[x]` | ISS-001 |
| FIX-002 | Pin ChromaDB Docker image to `0.6.3` | `[x]` | ISS-002 |
| FIX-003 | Add try/catch to all RAG FastAPI endpoints | `[x]` | ISS-003 |
| FIX-004 | `OllamaEmbeddingProvider.embed()` — handle `EmbedResponse` object vs dict | `[x]` | ISS-004 |
| FIX-005 | Seed data paths updated to `scripts/seed_data/` | `[x]` | — |
| FIX-006 | Unit tests for OllamaEmbeddingProvider (FIX-004 coverage) | `[x]` | 11/11 tests passing |
| FIX-007 | Journal filters (year/month) + scroll in EntryList sidebar | `[x]` | ISS-005 |
| FIX-008 | Nginx `proxy_read_timeout` 30s → 120s for LLM-backed endpoints | `[x]` | ISS-006 |
| FIX-009 | `rag_routes.py` embed-all: unpack `list_entries` tuple correctly | `[x]` | ISS-007 |
| FIX-010 | Integration test script `scripts/test_local_integration.sh` | `[x]` | ISS-008 |
| FIX-011 | Move CLI commands from AWS-Console-Setup.md to shell scripts | `[x]` | ISS-010 |

---

## Testing Status

| Area | Unit Tests | Integration Tests | Notes |
|---|---|---|---|
| RAG embed | `[x]` | `[x]` | 11 unit tests + integration (195/195 embedded) |
| RAG ask/search | `[ ]` | `[x]` | Integration: search + ask passing; conversation history: 8 unit tests passing |
| Bedrock LLM provider | `[x]` | `[ ]` | 6 unit tests passing (botocore stubber) |
| DynamoDB vector store | `[x]` | `[ ]` | 9 unit tests passing (moto) |
| Insights | `[ ]` | `[x]` | Integration: yearly summary generation passing |
| Entries CRUD | `[x]` | `[x]` | Full CRUD + count + bulk-delete; 20+ tests passing |
| Journal filters | `[ ]` | `[ ]` | UI only — no test setup yet |
| Admin dashboard | `[ ]` | `[ ]` | Existing feature, no tests yet |
| Auth (Cognito) | `[ ]` | `[ ]` | Existing feature, no tests yet |

---

| ISS-015 | AI Insights narrative shows raw JSON — LLM adds prose before/after JSON block, `json.loads` fails | `[x]` | `_extract_json()` in `interface.py` finds outermost `{…}` before parsing; 7 new unit tests passing |
| ISS-016 | Manage mode UX broken — entry titles invisible, no way to know what to do, delete button hidden until selection | `[x]` | Whole row clickable to toggle; "Delete selected" always visible (disabled when 0); titles bright in manage mode |
| ISS-017 | No way to delete user-level RAG index data | `[x]` | `DELETE /rag/vectors` calls `store.delete_all(tenant_id)`; "Clear index" button in Ask UI with confirmation dialog |

---

## Backlog

- Template 4 design and implementation
- Unit tests for insights and entries endpoints
- Frontend (Vitest) setup for journal filter component tests
- ISS-009: Fix burger menu icons on mobile
