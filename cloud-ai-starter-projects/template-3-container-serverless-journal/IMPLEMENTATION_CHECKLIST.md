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

---

## Testing Status

| Area | Unit Tests | Integration Tests | Notes |
|---|---|---|---|
| RAG embed | `[x]` | `[x]` | 11 unit tests + integration (195/195 embedded) |
| RAG ask/search | `[ ]` | `[x]` | Integration: search + ask passing |
| Insights | `[ ]` | `[x]` | Integration: yearly summary generation passing |
| Entries CRUD | `[ ]` | `[x]` | Integration: create/get/delete passing |
| Journal filters | `[ ]` | `[ ]` | UI only — no test setup yet |
| Admin dashboard | `[ ]` | `[ ]` | Existing feature, no tests yet |
| Auth (Cognito) | `[ ]` | `[ ]` | Existing feature, no tests yet |

---

## Backlog

- AWS deployment guide for RAG stack (Bedrock + OpenSearch)
- Template 4 design and implementation
- Unit tests for insights and entries endpoints
- Frontend (Vitest) setup for journal filter component tests
