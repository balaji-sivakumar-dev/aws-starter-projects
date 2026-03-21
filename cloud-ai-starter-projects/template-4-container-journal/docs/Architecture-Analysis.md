# Architecture Analysis — Template 3 Review & Platform Recommendations

> **Purpose**: Deep review of Template 3's architecture, evaluation of what scales to a multi-app platform, and concrete recommendations for Template 4.
>
> Last updated: 2026-03-14

---

## 1. Template 3 — What we built

Template 3 (Reflect Journal) is a full-stack serverless app with:

```
CloudFront → S3 (React SPA)
     │
     ▼
API Gateway v2 (HTTP, JWT auth)
     │
     ▼
Lambda (Python handler.py)
     ├── DynamoDB (single-table)
     └── Step Functions → AI Gateway Lambda → Groq / Bedrock
                                                     │
Cognito (Hosted UI, PKCE) ◄─────────────────────────┘
```

### Component inventory

| Component | Technology | Lines of code | Maturity |
|-----------|-----------|---------------|----------|
| Frontend | React 18 + Vite | ~1200 | Working — topnav, 3 tabs, auth, AI status polling |
| Lambda API | Python (raw handler) | ~350 | Working — all CRUD + insights + AI trigger |
| Core API (FastAPI) | Python (core + adapters) | ~1100 | Working — same logic, FastAPI/Docker deployment |
| Container API | Node.js Express | ~300 | Partial — missing Insights endpoints |
| AI Gateway | Python Lambda | ~300 | Working — entry enrichment + summary generation |
| Step Functions | ASL JSON | ~50 | Working — validate → invoke → complete/fail |
| Terraform | HCL (8 modules) | ~600 | Working — auth, db, compute, api, web, workflow, ai |
| Scripts | Bash (setup + destroy) | ~900 | Working — 5 setup steps + 4 destroy steps |
| Tests | pytest | ~800 | 28 passing — entries, insights, auth, LLM |

**Total: ~5600 lines** of application code + infrastructure.

---

## 2. Architecture patterns — evaluation

### 2.1 Core + Adapters — KEEP

```
services/api/src/
├── core/           ← Business logic (framework-agnostic)
│   ├── handlers.py
│   ├── repository.py
│   ├── models.py
│   └── auth.py
├── adapters/
│   ├── fastapi/    ← FastAPI routes (Docker deployment)
│   └── lambda_/    ← Lambda handler wrapper
└── llm/
    ├── interface.py  ← Abstract LLMProvider
    ├── factory.py    ← Provider factory
    └── providers/    ← Ollama, Groq, OpenAI, Bedrock
```

**Verdict**: This is the strongest pattern in Template 3. Business logic is completely separated from the deployment framework. The same `handlers.py` runs in Lambda, FastAPI, or App Runner.

**For the platform**: Elevate this to a convention. Every app follows `core/` + `adapters/` + `llm/`. The platform provides the adapters; apps only write `core/`.

**Rating: 9/10** — well-executed, no changes needed to the pattern itself.

---

### 2.2 LLM Provider Abstraction — KEEP + EXTEND

```python
class LLMProvider(ABC):
    @abstractmethod
    def enrich(self, title: str, body: str) -> dict: ...
    @abstractmethod
    def analyze_period(self, entries, period_label) -> dict: ...
```

**What works**: Swapping between Ollama (local), Groq (cloud), OpenAI, and Bedrock is a single env var change.

**What needs to change for the platform**:
- The interface methods (`enrich`, `analyze_period`) are journal-specific
- Platform needs a **generic completion interface**: `complete(prompt, system_prompt, max_tokens) → str`
- Apps bring their own prompt templates and response parsers
- The factory pattern and provider implementations stay the same

**Recommendation**:
```python
class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[dict], max_tokens: int = 1024) -> str: ...

    @abstractmethod
    def embed(self, text: str) -> list[float]: ...  # NEW — for RAG
```

Apps wrap this with domain-specific methods:
```python
# Budget Tracker example
def categorize_transaction(provider, description, amount):
    prompt = f"Categorize this transaction: {description} ${amount}..."
    return provider.complete([{"role": "user", "content": prompt}])
```

**Rating: 8/10** — pattern is right, interface needs generalizing.

---

### 2.3 DynamoDB Single-Table Design — KEEP + GENERALIZE

**Current key structure**:
```
PK: USER#{userId}
SK: ENTRY#{createdAt}#{entryId}       ← journal entries
SK: ENTRYID#{entryId}                 ← lookup index
SK: SUMMARY#{summaryId}               ← period summaries
```

**What works**: Efficient single-table access, pay-per-request pricing, no provisioning.

**What needs to change**:
- Key prefixes are journal-specific (`ENTRY#`, `SUMMARY#`)
- No support for multi-tenancy (organizations, shared data)
- No support for relationships between entities (Family Tree needs graph-like queries)

**Recommended generic key patterns**:
```
PK: TENANT#{tenantId}              ← org/user isolation
SK: {ENTITY_TYPE}#{sortKey}        ← extensible per app

Examples per app:
Budget:    TENANT#user1 | TXN#2026-01-15#txn123
Tax:       TENANT#user1 | DOC#2026#t4-001
Curriculum: TENANT#org1 | COURSE#cs101#MODULE#1
Family:    TENANT#user1 | PERSON#person123
```

**For graph-like queries (Family Tree)**:
```
PK: PERSON#{personId}
SK: REL#{relationshipType}#{targetPersonId}

With GSI (inverted):
GSI1PK: PERSON#{targetPersonId}
GSI1SK: REL#{relationshipType}#{personId}
```

This allows bidirectional traversal without a graph database.

**Rating: 7/10** — solid foundation, needs entity abstraction and optional GSI patterns.

---

### 2.4 Async AI via Step Functions — KEEP + GENERALIZE

**Current**: Single state machine handles both entry enrichment and summary generation via a Choice state.

**What works**: Decouples UI from LLM latency, handles retries, logs execution history.

**What needs to change**:
- State machine is hardcoded for two task types (entry/summary)
- Platform needs a **generic async task pattern**:
  - Task type is a parameter, not a hardcoded choice
  - Different apps register different task handlers
  - Common: validate → route → invoke → update status → complete/fail

**Recommended approach**:
```json
// Generic task input
{
  "taskType": "categorize_transactions",  // or "generate_exam", "extract_tax_fields"
  "tenantId": "user123",
  "entityId": "txn-batch-001",
  "payload": { ... }
}
```

The AI Gateway Lambda becomes a **task router** — reads `taskType`, calls the appropriate handler function.

**Rating: 7/10** — pattern works, needs parameterization.

---

### 2.5 Authentication (Cognito) — KEEP + EXTEND

**What works**:
- PKCE flow (no client secret, secure for SPAs)
- Hosted UI (zero custom login pages to maintain)
- `given_name`/`family_name` in schema
- `id_token` decoded client-side for display name/email

**What needs to change for multi-app platform**:
- **User roles**: Some apps need admin/member roles (Curriculum: teacher/student)
- **Cognito Groups**: Map to roles, use `cognito:groups` claim in JWT
- **Per-app user pools vs shared pool**: Shared pool saves cost; separate pools give isolation

**Recommendation**: Start with a single Cognito user pool. Use Cognito Groups for roles. Add `custom:role` attribute if groups aren't sufficient. This keeps auth infrastructure simple while supporting role-based access.

**Rating: 8/10** — solid, just needs groups/roles.

---

### 2.6 Frontend Architecture — KEEP SHELL + REBUILD PER APP

**What works**:
- React + Vite is fast to develop and build
- Auth flow (PKCE + local bypass) is clean
- API client wrapper handles auth headers transparently

**What's too coupled**:
- `App.jsx` has hardcoded tabs (Home/Journal/Insights)
- Components are journal-specific
- No component library or design system
- `styles.css` is a single monolithic file

**Recommendation for platform**:
- Extract a **reusable app shell**: auth provider, nav layout, API client, config loader
- Apps plug in their own routes, tabs, and components
- Consider a lightweight component library (or just consistent CSS patterns)
- Keep `styles.css` per-app (not worth a design system at this stage)

**Rating: 6/10** — auth/API layer is reusable, UI components are not.

---

### 2.7 Terraform Modules — KEEP + PARAMETERIZE

**Current modules** (8):
| Module | Reusable as-is? |
|--------|-----------------|
| `auth/` | ✅ Yes — just change schema attributes |
| `db/` | ✅ Yes — table name parameterized |
| `compute_lambda/` | ✅ Yes — source_dir is a variable |
| `compute_container/` | ⚠️ Needs IAM instance role fix |
| `api_edge/` | ✅ Yes — routes passed as variable map |
| `web_hosting/` | ✅ Yes — fully generic |
| `ai_gateway/` | ⚠️ Slightly coupled (journal table ARN) |
| `workflow/` | ✅ Yes — definition path is a variable |

**Recommendation**: 6 of 8 modules are already reusable. Fix `compute_container` (add instance IAM role) and generalize `ai_gateway` (accept any table ARN, not just "journal"). Then any new app can compose the same modules with different variables.

**Rating: 8/10** — well-modularized, minor fixes needed.

---

### 2.8 Scripts — KEEP PATTERN + PARAMETERIZE

**Current**: `scripts/setup/step-1` through `step-5`, `scripts/destroy/step-1a` through `step-1d`.

**What works**: Numbered steps with clear order, idempotent, env-parameterized.

**What to change**:
- Hardcoded paths to `services/lambda_api/src` and `apps/web/`
- Lambda zip cache management is compute-mode specific
- Consider a `config.sh` that each app sources for paths/names

**Rating: 7/10** — pattern is excellent, needs minor parameterization.

---

### 2.9 Docker Compose Local Dev — KEEP

**What works**:
- `docker-compose.yml` (base) + overlays (`docker-compose.groq.yml`, etc.)
- DynamoDB Local for zero-AWS development
- Same API code runs locally and in AWS

**What to add**:
- LocalStack for S3 (file upload testing) and SFN (workflow testing)
- Or keep S3/SFN as AWS-only features and mock locally

**Rating: 8/10** — clean, overlay pattern is great.

---

## 3. New capabilities needed

### 3.1 RAG Pipeline (see [`RAG-Design.md`](RAG-Design.md))

Budget Tracker needs: "How much did I spend on groceries in Q1?"
Curriculum needs: "Explain polymorphism using examples from my course materials."
Tax Processor needs: "What deductions apply to my situation based on uploaded documents?"

RAG is a cross-cutting concern. The platform should provide:
1. **Embedding service** — chunk text, generate vectors
2. **Vector store** — store and query embeddings
3. **Retrieval API** — find relevant context for a user query
4. **LLM integration** — pass retrieved context + user query to LLM

### 3.2 File Upload & Processing Pipeline

Budget Tracker: CSV/Excel transaction files
Tax Processor: PDF tax documents
Curriculum: PDF/text learning materials
Family Tree: Photos

**Recommended architecture**:
```
Client → Pre-signed S3 URL → S3 bucket
                                  │
                                  ▼ (S3 event notification)
                          Step Functions
                                  │
                          ┌───────┴───────┐
                          ▼               ▼
                    Parse/Extract     Embed (RAG)
                    (Lambda)          (Lambda)
                          │               │
                          ▼               ▼
                      DynamoDB      Vector Store
```

- Pre-signed URLs avoid API Gateway payload limits (10 MB)
- Step Functions orchestrate multi-step processing
- Parsers are app-specific (CSV parser for Budget, Textract for Tax)
- Embedding is shared infrastructure

### 3.3 AI Cost Tracking & Audit

Every AI call should log:
```json
{
  "timestamp": "2026-03-14T10:30:00Z",
  "tenantId": "user123",
  "taskType": "categorize_transaction",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "inputTokens": 450,
  "outputTokens": 120,
  "latencyMs": 1200,
  "estimatedCost": 0.0003
}
```

**Implementation**: Middleware in the LLM provider abstraction that wraps every `complete()` call, extracts token counts from the response, and writes to a DynamoDB audit table (or CloudWatch Logs for cheaper storage).

### 3.4 Subscription / Usage Tiers (future)

Not for initial implementation, but the architecture should accommodate:
- Free tier: N AI queries/month, M file uploads
- Paid tier: unlimited, higher rate limits
- Usage metering based on AI audit logs
- Stripe integration for payment (future phase)

**Architectural impact**: Add a `TENANT#{tenantId} | USAGE#{month}` item in DynamoDB to track monthly consumption. Check against tier limits before processing AI requests.

---

## 4. Recommended platform architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Shell                        │
│  React SPA + Auth (Cognito PKCE) + Configurable Nav     │
│  CloudFront → S3                                         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│               API Gateway v2 (HTTP + JWT)                │
│  Routes defined per app, JWT authorizer shared           │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Lambda   │ │ App      │ │ Lambda   │
    │ API      │ │ Runner   │ │ AI       │
    │ (Python) │ │ (Docker) │ │ Gateway  │
    └────┬─────┘ └────┬─────┘ └────┬─────┘
         │            │            │
    ┌────┴────────────┴────┐  ┌───┴──────────┐
    │     DynamoDB         │  │ Step          │
    │  (single-table,      │  │ Functions     │
    │   per-app prefix)    │  │ (async tasks) │
    └──────────────────────┘  └──────────────┘
                                    │
                              ┌─────┴─────┐
                              ▼           ▼
                        ┌──────────┐ ┌──────────┐
                        │ LLM      │ │ Embedding│
                        │ Provider │ │ Service  │
                        │ (Groq/   │ │ (Titan/  │
                        │  Bedrock)│ │  Cohere) │
                        └──────────┘ └─────┬────┘
                                           │
                                      ┌────┴────┐
                                      │ Vector  │
                                      │ Store   │
                                      │ (AOSS/  │
                                      │  Pinecone│
                                      │  /local) │
                                      └─────────┘

    ┌─────────────────────────────────────────────┐
    │              S3 (File Storage)               │
    │  Upload via pre-signed URL → event → process │
    └─────────────────────────────────────────────┘
```

---

## 5. Cost analysis — Template 3 baseline

Template 3's architecture is optimized for low-traffic/early-stage apps:

| Service | Pricing model | Cost at 0 users | Cost at 100 DAU |
|---------|--------------|------------------|-----------------|
| Lambda | Per-request | $0 (free tier) | ~$0.20/mo |
| API Gateway | Per-request | $0 (free tier) | ~$1/mo |
| DynamoDB | Per-request | $0 (free tier) | ~$2/mo |
| S3 + CloudFront | Storage + transfer | ~$0.50/mo | ~$2/mo |
| Cognito | Per-MAU | $0 (first 50K free) | $0 |
| Step Functions | Per-transition | $0 (free tier) | ~$0.10/mo |
| **Subtotal (no AI)** | | **~$0.50/mo** | **~$5/mo** |
| Groq (AI) | Per-token | Depends on usage | ~$2-10/mo |
| Bedrock (AI) | Per-token | Depends on usage | ~$5-20/mo |

**Key insight**: The serverless architecture costs nearly nothing at zero scale. This is ideal for bootstrapping multiple apps — you only pay for what you use.

**Container alternative** (App Runner): Minimum ~$7/mo per service (0.25 vCPU always-on). Use containers only when cold-start latency matters or when the app needs persistent connections.

**Recommendation**: Start every app serverless (Lambda). Migrate to containers only if latency or connection persistence becomes a problem.

---

## 6. Summary — what to do next

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 1 | Generalize LLM interface (`complete()` + `embed()`) | High | Small |
| 2 | Design RAG pipeline (see RAG-Design.md) | High | Medium |
| 3 | Add file upload pipeline (S3 + pre-signed URLs + processing) | High | Medium |
| 4 | Fix `compute_container` IAM role | Medium | Small |
| 5 | Extract reusable frontend shell (auth + nav + API client) | Medium | Medium |
| 6 | Parameterize Terraform modules for any app | Medium | Small |
| 7 | Add AI cost tracking middleware | Medium | Small |
| 8 | Build first app (Budget Tracker) on the platform | High | Large |
| 9 | Add Cognito groups for user roles | Low | Small |
| 10 | Subscription/billing hooks | Low | Large |

The strongest path forward: **Build the RAG pipeline first** (it's needed by 3 of 4 target apps), then build the Budget Tracker as the first app on the platform. The Budget Tracker exercises file upload (CSV/Excel), AI categorization, RAG queries, and all the core infrastructure — making it the best test of the platform's generality.
