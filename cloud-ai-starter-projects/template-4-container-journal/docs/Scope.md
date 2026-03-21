# Template 4 — Platform Scope & Target Applications

> **Status: Design phase**
> Last updated: 2026-03-14

---

## 1. Vision

Build a **reusable full-stack platform template** that can bootstrap multiple AI-powered applications. Each app gets authentication, data storage, API layer, AI/RAG capabilities, file processing, and deployment automation out of the box — then adds its own business logic on top.

The motivation: save cost and time in the initial phase of each project. Start with a proven architecture, deploy cheaply (pay-per-use), and scale when customer base and revenue grow.

---

## 2. Target Applications

### 2.1 Personal Budget Tracker

| Aspect | Detail |
|--------|--------|
| **Input** | Transaction exports from banks/credit cards (CSV, Excel, PDF) |
| **Processing** | Parse documents → extract transactions → auto-categorize |
| **Storage** | Transactions, categories, budgets, accounts |
| **AI** | Smart categorization, spending pattern analysis, budget recommendations |
| **RAG** | Query past spending: "How much did I spend on dining in January?" |
| **Unique needs** | Multi-format document parsing, recurring pattern detection, budget vs actual calculations |

### 2.2 Tax Processor

| Aspect | Detail |
|--------|--------|
| **Input** | Tax documents (T4, T5, receipts, investment statements) |
| **Processing** | OCR/scan → extract structured data → map to tax form fields |
| **Storage** | Tax profiles, documents, extracted fields, submissions |
| **AI** | Document classification, field extraction, deduction suggestions |
| **RAG** | Query tax rules: "Am I eligible for the home office deduction?" |
| **Unique needs** | OCR pipeline, external tax API integration, compliance-grade audit trail |

### 2.3 Curriculum Platform

| Aspect | Detail |
|--------|--------|
| **Input** | Learning materials (PDFs, text, videos, URLs) |
| **Processing** | Ingest content → chunk → embed → generate training materials |
| **Storage** | Courses, modules, exams, student progress, scores |
| **AI** | Generate MCQs, theory assignments, personalized study plans |
| **RAG** | Query course content: "Explain the concept of polymorphism with examples from Module 3" |
| **Unique needs** | Exam engine (MCQ + theory + answer-based), scoring, performance analytics, personalized learning paths |

### 2.4 Family Tree

| Aspect | Detail |
|--------|--------|
| **Input** | Family member profiles, photos, relationship definitions |
| **Processing** | Build/traverse graph relationships, classify connections |
| **Storage** | People, relationships (parent/child/spouse/sibling), media |
| **AI** | Relationship inference, photo tagging, story generation from family history |
| **RAG** | Query family: "Who are all the descendants of my grandfather?" |
| **Unique needs** | Graph data model (or adjacency list in DynamoDB), bidirectional relationship traversal, media uploads, sharing/permissions |

---

## 3. Shared Platform Capabilities

These are the capabilities every app needs. The platform template provides them out of the box:

| # | Capability | Template 3 status | Platform action |
|---|-----------|-------------------|-----------------|
| 1 | **Authentication & user management** | ✅ Cognito PKCE + hosted UI | Generalize — add user roles, profile management |
| 2 | **API layer** | ✅ Lambda + API Gateway | Keep — add request validation middleware, rate limiting |
| 3 | **Structured data storage** | ✅ DynamoDB single-table | Generalize — define entity patterns, not journal-specific keys |
| 4 | **LLM integration** | ✅ Provider abstraction (Groq/Bedrock/Ollama) | Keep as-is — already portable |
| 5 | **Async AI pipeline** | ✅ Step Functions + AI Gateway Lambda | Generalize — support multiple workflow types |
| 6 | **Frontend SPA** | ✅ React + Vite + CloudFront | Keep — extract reusable shell (auth, nav, layout) |
| 7 | **Local dev** | ✅ Docker Compose + DynamoDB Local | Keep — add LocalStack for S3/SFN if needed |
| 8 | **IaC** | ✅ Terraform modules | Generalize — parameterize for any app |
| 9 | **Setup/destroy scripts** | ✅ Numbered steps | Keep pattern — parameterize app name |
| 10 | **RAG / vector search** | ❌ Not built | **New** — embeddings + vector store + retrieval |
| 11 | **File upload & processing** | ❌ Not built | **New** — S3 upload + processing pipeline |
| 12 | **Audit / cost tracking** | ❌ Not built | **New** — log AI calls, token usage, cost per request |
| 13 | **Subscription / billing** | ❌ Not built | **New** — usage tiers, Stripe integration (future) |
| 14 | **Multi-tenancy** | ❌ Not built | **New** — org/tenant isolation in DynamoDB |

---

## 4. App-Specific Layers (built on top of the platform)

Each app adds its own:

| Layer | What's custom |
|-------|--------------|
| **Data model** | Entity types, relationships, validation rules |
| **Business logic** | Domain handlers (budget calculations, tax rules, exam scoring, graph traversal) |
| **AI prompts** | Domain-specific LLM prompts and response parsers |
| **RAG knowledge base** | What gets embedded, how it's chunked, what queries are supported |
| **UI components** | Domain-specific views (budget charts, tax forms, exam interface, family tree visualization) |
| **File processors** | CSV parser, PDF extractor, image handler — each app needs different parsers |

---

## 5. What Template 3 validated

Template 3 proved these architectural patterns work end-to-end:

| Pattern | Evidence |
|---------|----------|
| Core + Adapters | `services/api/src/core/` (business logic) + `adapters/fastapi/` + `adapters/lambda_/` — same logic, two runtimes |
| LLM Provider Abstraction | `services/api/src/llm/` — swap Ollama/Groq/OpenAI/Bedrock via env var, zero code changes |
| Single-table DynamoDB | `USER#{id}` + `ENTRY#`, `SUMMARY#`, `ENTRYID#` sort keys — flexible, performant |
| Async AI via Step Functions | Entry enrichment + period summary generation — decoupled from request/response |
| Dual-mode auth | Local (`X-User-Id` header) + AWS (Cognito PKCE) — same API, different auth middleware |
| Compute flexibility | Lambda (serverless) / App Runner (container) / Hybrid — controlled by `compute_mode` variable |
| Docker Compose local dev | Full stack runs locally with DynamoDB Local + LLM overlays |
| Scripted deployment | Numbered setup steps: bootstrap → apply → deploy → verify |

---

## 6. What needs to change for the platform

These are the areas where Template 3's architecture is too tightly coupled to the journal domain and needs to be generalized:

| Area | Current (Template 3) | Needed (Platform) |
|------|---------------------|-------------------|
| **DynamoDB keys** | `USER#{userId}` + `ENTRY#{date}#{id}` hardcoded | Generic entity pattern: `TENANT#{id}` + `{EntityType}#{sortKey}` |
| **API routes** | `/entries`, `/insights/summaries` — journal-specific | Route registration pattern — each app defines its own routes |
| **Step Functions** | Single workflow for entry + summary AI | Workflow registry — apps register their own async tasks |
| **Frontend shell** | Topnav with Home/Journal/Insights tabs | Configurable nav — apps define their own tabs and routes |
| **AI prompts** | Journal summarization + tag extraction | Prompt templates — apps bring their own prompts, platform handles LLM calls |
| **File handling** | None | S3 upload + event-driven processing pipeline (new capability) |
| **RAG** | None | Embedding + vector store + retrieval layer (new capability) |
| **Cost tracking** | None | Middleware to log token usage, model, latency per AI call |

---

## 7. Implementation priorities

### Phase 1 — Foundation (extract from Template 3)
- Extract reusable Terraform modules into shared module library
- Define generic DynamoDB entity patterns
- Create app scaffold generator (cookiecutter or script)
- Set up shared frontend shell (auth + nav + layout)

### Phase 2 — RAG pipeline
- Embedding service (chunk text → generate embeddings)
- Vector store (OpenSearch Serverless or DynamoDB + approximate search)
- Retrieval API (query → similar documents → context for LLM)
- Integration with existing LLM provider abstraction

### Phase 3 — File processing pipeline
- S3 upload endpoint (pre-signed URLs)
- Event-driven processing (S3 → Lambda/Step Functions)
- Document parsers: CSV, Excel, PDF (Textract or open-source)
- Parsed data → DynamoDB + optional RAG embedding

### Phase 4 — First app (Budget Tracker)
- Build on platform foundation
- CSV/Excel transaction import
- Auto-categorization via LLM
- Budget planning + expense tracking
- RAG queries on spending history

### Phase 5 — Operational maturity
- AI cost tracking + audit logs
- Usage tiers + subscription hooks
- Multi-tenancy patterns
- CI/CD pipeline templates
