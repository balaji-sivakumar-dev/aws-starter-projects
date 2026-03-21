# RAG + Admin Implementation Checklist

> **Status: In Progress**
> Last updated: 2026-03-14

---

## Use case: "Ask Your Journal"

Semantic search + conversational AI over journal entries. Users can ask questions like:
- "What was I stressed about last month?"
- "Find entries where I talked about career goals"
- "What recurring themes appear in my writing?"
- "When did I last feel really happy?"

This exercises the full RAG pipeline: embed entries → store vectors → retrieve context → generate answer with citations.

---

## Phase 1 — RAG Backend (Local)

### 1.1 Embedding Provider Abstraction
- [x] Create `services/api/src/rag/__init__.py`
- [x] Create `services/api/src/rag/embedding.py` — `EmbeddingProvider` ABC with `embed()`, `embed_batch()`, `dimensions` property
- [x] Implement `OllamaEmbeddingProvider` — uses `nomic-embed-text` model via HTTP
- [x] Implement `TitanEmbeddingProvider` — uses `amazon.titan-embed-text-v2:0` via Bedrock (for AWS deploy later)
- [x] Create `services/api/src/rag/embedding_factory.py` — factory that reads `EMBEDDING_PROVIDER` env var

### 1.2 Vector Store Abstraction
- [x] Create `services/api/src/rag/store.py` — `VectorStore` ABC with `upsert()`, `search()`, `delete()`, `count()`
- [x] Implement `ChromaDBStore` — uses ChromaDB Python client, tenant-isolated collections
- [x] Add `chromadb` to `requirements.txt`

### 1.3 Retriever + RAG Query Service
- [x] Create `services/api/src/rag/retriever.py` — orchestrates embed query → search vectors → return documents
- [x] Create `services/api/src/rag/rag_service.py` — retriever + LLM completion for conversational answers

### 1.4 RAG API Endpoints
- [x] Create `services/api/src/adapters/fastapi/rag_routes.py`
  - [x] `POST /rag/ask` — user question → retrieve context → LLM answer with source citations
  - [x] `POST /rag/search` — semantic search only (no LLM, returns matching entries)
  - [x] `POST /rag/embed` — manually trigger embedding for a specific entry
  - [x] `POST /rag/embed-all` — bulk embed all user's entries (initial setup / re-index)
  - [x] `GET /rag/status` — embedding stats (total vectors, last embedded)
- [x] Register router in `app.py`

### 1.5 Ingestion (Auto-embed on write)
- [ ] Modify `services/api/src/core/handlers.py` — after `create_entry` and `update_entry`, trigger embedding
- [ ] Embed entry text: `"{title}\n\n{body}"` as the chunk
- [ ] Store metadata: `entryId`, `userId`, `createdAt`, `title` (for citation)

---

## Phase 2 — RAG Frontend (Local)

### 2.1 Docker Compose
- [x] Create `docker-compose.rag.yml` overlay — adds ChromaDB service + embedding model
- [ ] Update `docker-compose.ollama.yml` — add `nomic-embed-text` to model pull list
- [ ] Document usage: `docker compose -f docker-compose.yml -f docker-compose.ollama.yml -f docker-compose.rag.yml up`

### 2.2 Frontend — "Ask" Tab
- [x] Create `apps/web/src/api/rag.js` — API client for RAG endpoints
- [x] Create `apps/web/src/components/AskJournal.jsx` — chat-style UI
  - [ ] Input box for questions
  - [ ] Answer display with source citations (linked to journal entries)
  - [ ] Conversation history within session
  - [ ] Loading state while LLM generates answer
  - [ ] Semantic search mode toggle (search-only vs conversational)
- [x] Add "Ask" tab to topnav in `App.jsx`
- [x] Add styles for chat UI in `styles.css`

### 2.3 Embedding Status + Controls
- [ ] Add embedding status indicator to Dashboard (e.g., "42 entries embedded")
- [ ] Add "Re-index all entries" button (calls `POST /rag/embed-all`)
- [ ] Show embedding progress indicator

---

## Phase 3 — Admin & Audit

### 3.1 Audit Logging
- [x] Create `services/api/src/core/audit.py` — audit logger
  - [ ] Log AI calls: provider, model, input/output tokens, latency, cost estimate
  - [ ] Log user actions: login, entry CRUD, AI requests, RAG queries
  - [ ] Log RAG queries: question, retrieved docs count, answer length
- [ ] Store audit records in DynamoDB: `PK: AUDIT#{date}`, `SK: {timestamp}#{eventId}`
- [ ] Add audit middleware to FastAPI (wraps AI provider calls)

### 3.2 Admin Role
- [ ] Define admin user identification: env var `ADMIN_USER_IDS` (comma-separated user IDs)
- [x] Create `services/api/src/adapters/fastapi/admin_routes.py`
- [ ] Add `is_admin()` dependency check in `deps.py`
- [ ] Register admin router in `app.py` (prefix: `/admin`)

### 3.3 Admin API Endpoints
- [ ] `GET /admin/users` — list all users (distinct PK prefixes from DynamoDB scan)
- [ ] `GET /admin/users/{userId}/activity` — user's recent actions from audit log
- [ ] `GET /admin/metrics` — aggregate stats:
  - [ ] Total users, active users (last 7/30 days)
  - [ ] Total entries, entries created this week/month
  - [ ] Total AI calls, AI calls by provider/model
  - [ ] Total RAG queries, avg retrieved docs, avg answer latency
  - [ ] Estimated AI cost breakdown
- [ ] `GET /admin/audit` — paginated audit log with filters (user, action, date range)

### 3.4 Admin Dashboard (Frontend)
- [ ] Create `apps/web/src/components/AdminPanel.jsx`
  - [ ] User list with activity summary
  - [ ] Usage metrics charts (entries/day, AI calls/day, cost/day)
  - [ ] Audit log viewer with filters
  - [ ] RAG index health (total vectors, embedding coverage)
- [ ] Add "Admin" tab to topnav (visible only to admin users)
- [ ] Add admin styles

---

## Phase 4 — AWS Deployment

### 4.1 Infrastructure
- [ ] Create `infra/terraform/modules/rag/` — vector store infrastructure
  - [ ] DynamoDB table for vectors (MVP) or OpenSearch Serverless (scale)
  - [ ] IAM permissions for Bedrock embedding model
- [ ] Update `ai_gateway` module — add Bedrock embedding permissions
- [ ] Update Lambda handler for RAG endpoints
- [ ] Add `EMBEDDING_PROVIDER`, `RAG_STORE` env vars to Lambda config

### 4.2 Scripts
- [ ] Update `scripts/setup/step-2b-store-secrets.sh` — add any RAG-related secrets
- [ ] Update `scripts/setup/step-3a-terraform-apply.sh` — include RAG module
- [ ] Create `scripts/seed-embeddings.sh` — bulk embed existing entries after deploy

### 4.3 Testing
- [ ] Test RAG query via CloudFront URL
- [ ] Test admin dashboard via CloudFront
- [ ] Verify audit logging in DynamoDB
- [ ] Verify embedding on entry create/update via Step Functions

---

## File inventory (what we'll create/modify)

### New files
```
services/api/src/rag/__init__.py
services/api/src/rag/embedding.py
services/api/src/rag/embedding_factory.py
services/api/src/rag/store.py
services/api/src/rag/retriever.py
services/api/src/rag/rag_service.py
services/api/src/core/audit.py
services/api/src/adapters/fastapi/rag_routes.py
services/api/src/adapters/fastapi/admin_routes.py
apps/web/src/api/rag.js
apps/web/src/components/AskJournal.jsx
apps/web/src/components/AdminPanel.jsx
docker-compose.rag.yml
```

### Modified files
```
services/api/requirements.txt              ← add chromadb
services/api/src/adapters/fastapi/app.py   ← register rag + admin routers
services/api/src/adapters/fastapi/deps.py  ← add is_admin dependency
services/api/src/core/handlers.py          ← embed on create/update entry
services/api/src/llm/interface.py          ← add generic complete() method
docker-compose.ollama.yml                  ← add nomic-embed-text model
apps/web/src/App.jsx                       ← add Ask + Admin tabs
apps/web/src/styles.css                    ← chat + admin styles
apps/web/src/api/client.js                 ← no changes expected
.env.local.example                         ← add RAG env vars
```
