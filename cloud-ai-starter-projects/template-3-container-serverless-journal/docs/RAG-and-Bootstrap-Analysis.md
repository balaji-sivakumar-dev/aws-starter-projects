# RAG Integration & Bootstrap Template Analysis

Two independent topics are covered here:

1. **RAG for the journal app** — do we need it, how to add it locally and on AWS
2. **Using this as a bootstrap template** — how to fork and adapt it for a new app

---

## Part 1 — RAG for the Journal App

### What is RAG?

Retrieval-Augmented Generation (RAG) augments an LLM prompt with relevant documents retrieved from a vector store. Instead of asking the LLM to "know" everything, you first search your own data for the most relevant passages, then pass those passages to the LLM alongside the user's question.

```
User question
    ↓
Embed question → search vector store → retrieve top-K chunks
    ↓
Prompt = [system instructions] + [retrieved chunks] + [user question]
    ↓
LLM → answer grounded in your data
```

### Do we need RAG for this journal app?

**Short answer: yes, for the "ask questions about past entries" use case.**

The current AI features (per-entry summary + period insights) work on a single entry or a bounded date range — the LLM never needs to see the full history. But if you want to support:

- _"What ideas have I had about X over the past year?"_
- _"When did I last write about feeling overwhelmed at work?"_
- _"Summarise everything I've written about my side project"_

…then you need RAG, because the full journal history is too large to fit in a single prompt, and keyword search misses semantic matches.

### What changes are needed?

#### New components

| Component | Purpose | Local option | AWS option |
|-----------|---------|-------------|------------|
| Vector store | Store embeddings of entry chunks | Chroma (Docker) | OpenSearch Serverless or pgvector on RDS |
| Embedding model | Convert text → vector | Ollama (`nomic-embed-text`) or Groq | Amazon Titan Embeddings or Groq |
| RAG Lambda / endpoint | New `POST /chat` route | Local FastAPI | Lambda + API Gateway |
| Indexing trigger | Embed entry after save/update | Background task | Lambda triggered on DynamoDB Streams |

#### Data flow

```
On entry create/update:
  entry.body → embedding model → vector → stored in vector store
  metadata: { userId, entryId, createdAt }

On user question:
  question → embedding model → search vector store (filter by userId)
  → top-5 chunks retrieved
  → prompt = chunks + question → Groq/Bedrock → answer
```

#### DynamoDB Streams approach (AWS)

Enable DynamoDB Streams on the journal table, then attach a Lambda that:
1. Reads the new/updated entry
2. Calls an embedding API (Groq `llama-3.1-8b-instant` supports embeddings via OpenAI-compatible endpoint, or use Amazon Titan Embeddings)
3. Upserts the vector in OpenSearch Serverless

This is fully event-driven — no polling, no changes to existing write paths.

### Should entries be chunked?

| Entry size | Approach |
|------------|----------|
| < 1000 chars | Store as one vector per entry |
| 1000–5000 chars | Split into paragraphs, one vector each |
| > 5000 chars | Sliding window chunking (500 token chunks, 100 token overlap) |

For a personal journal, most entries will be short — one vector per entry is fine to start.

### Local testing stack

```
docker-compose.yml          ← existing stack (DynamoDB Local, API, Web)
docker-compose.rag.yml      ← adds Chroma + embedding sidecar
```

```bash
# Start with RAG support
docker compose -f docker-compose.yml -f docker-compose.rag.yml up --build
```

New containers:
- `t3-chroma` — Chroma vector DB (port 8001)
- `t3-embed` — embedding sidecar (wraps Ollama or a lightweight sentence-transformers model)

New env vars injected into the API:
```bash
RAG_ENABLED=true
CHROMA_HOST=http://chroma:8001
EMBED_MODEL=nomic-embed-text
```

New API route:
```
POST /chat
Body: { "question": "What have I written about..." }
Response: { "answer": "...", "sources": [{ entryId, title, createdAt }] }
```

### AWS testing stack

| Service | Role | Cost at low traffic |
|---------|------|---------------------|
| Amazon OpenSearch Serverless (vector collection) | Vector store | ~$0.24/OCU-hr, min 2 OCUs ≈ $350/month — **expensive** |
| pgvector on RDS PostgreSQL | Vector store | t3.micro ~$15/month |
| DynamoDB Streams | Indexing trigger | Included in DynamoDB free tier |
| Lambda (indexing) | Embed + upsert on write | ~$0 at low traffic |
| Lambda (chat) | RAG query handler | ~$0 at low traffic |

**Recommendation for dev/test:** Use **pgvector on RDS PostgreSQL** (t3.micro) instead of OpenSearch Serverless. It's 20x cheaper for low-traffic testing and the pgvector extension handles vector similarity search natively.

For production with high query volume, migrate to OpenSearch Serverless.

### Implementation effort estimate

| Phase | What | Effort |
|-------|------|--------|
| 1 | Add `/chat` route + Chroma local stack | 1–2 days |
| 2 | DynamoDB Streams indexing Lambda | 1 day |
| 3 | AWS pgvector RDS + Terraform module | 2 days |
| 4 | Connect embedding + search to Groq/Bedrock | 1 day |

### Recommendation

Add RAG if you plan to support the "ask questions about past entries" use case. The architecture fits naturally into the existing event-driven pattern (Streams → Lambda → vector store, same as DynamoDB → Step Functions → LLM today). Start with Chroma locally and pgvector on RDS for AWS dev testing.

---

## Part 2 — Using This as a Bootstrap Template

### What this template provides out of the box

| Concern | What's included |
|---------|----------------|
| Auth | Cognito PKCE flow, JWT validation, callback URL auto-config |
| API | Lambda (serverless) or App Runner (container) or both (hybrid) |
| DB | DynamoDB single-table, soft deletes, pagination |
| AI | Async enrichment via Step Functions + Groq/Bedrock Lambda |
| Web | React + Vite, Cognito auth, API client, token refresh |
| Infra | Terraform modules, automated setup/destroy scripts |
| CI/CD-ready | S3 + CloudFront deploy, backend state in S3 |

### Approach 1 — Fork and rename (recommended for a new app)

This is the cleanest approach. Every resource name is driven by `app_prefix` and `env` in `dev.tfvars`, so renaming the app is a single-line change.

**Steps:**

1. Copy the template directory to a new folder:
   ```bash
   cp -r template-3-container-serverless-journal my-new-app
   cd my-new-app
   ```

2. Update `dev.tfvars` (and `dev.tfvars.example`):
   ```hcl
   app_prefix = "myapp"   # was "journal" — changes all resource names
   env        = "dev"
   aws_region = "ca-central-1"
   ```

3. All AWS resources will be named `myapp-dev-*` instead of `journal-dev-*`. No Terraform changes needed.

4. Replace the data model in `services/lambda_api/src/handler.py` with your entity types.

5. Replace the React components in `apps/web/src/` with your UI.

6. Run `step-2` + `step-3a` to provision a fresh stack for the new app — the Cognito domain, DynamoDB table, Lambda, API Gateway, and CloudFront are all brand new.

### Approach 2 — Multi-app from one repo (monorepo)

If you want multiple apps in the same repo, add a new directory alongside `template-3-container-serverless-journal`:

```
cloud-ai-starter-projects/
  template-3-container-serverless-journal/   ← original
  my-notes-app/                              ← new app, same structure
  my-crm-app/                                ← another app
```

Each app has its own:
- `infra/terraform/` (separate state bucket per app, different `app_prefix`)
- `services/` (independent Lambda/container code)
- `apps/web/` (independent React app)
- `scripts/setup/` and `scripts/destroy/`

Pros: easy to compare implementations, share utility scripts
Cons: repo grows large, CI pipelines need path filtering

### What to customise when building a new app

| File/location | What to change |
|--------------|----------------|
| `dev.tfvars` | `app_prefix` — renames all AWS resources |
| `services/lambda_api/src/handler.py` | Replace journal CRUD with your entity types |
| `services/workflows/src/ai_gateway.py` | Replace journal enrichment prompt with your AI task |
| `apps/web/src/` | Replace React components with your UI |
| `services/workflows/statemachine/*.asl.json` | Replace or extend the Step Functions state machine |
| `infra/terraform/modules/db/main.tf` | Add GSIs if your access patterns need them |

### What you can keep unchanged

- All auth infrastructure (Cognito, JWT, PKCE) — works for any app
- API Gateway setup (CORS, JWT authorizer, routes pattern)
- CloudFront + S3 web hosting
- Step Functions + async Lambda pattern
- All setup/destroy scripts (just change `app_prefix`)
- Terraform backend bootstrapping

### Multi-environment support

The scripts and Terraform are already parameterised by `ENV_NAME`. To add a staging environment:

```bash
cp infra/terraform/environments/dev/dev.tfvars \
   infra/terraform/environments/staging/staging.tfvars
# Edit: env = "staging", point to staging Cognito URLs etc.

./scripts/setup/step-3a-terraform-apply.sh staging
```

Each environment gets its own isolated stack of AWS resources.

### Summary

| Scenario | Recommended approach |
|----------|---------------------|
| Build a new solo app | Fork + change `app_prefix` + replace handler + replace UI |
| Multiple apps, same repo | Add sibling directories, one `app_prefix` per app |
| Add an environment (staging/prod) | Add a new `environments/<env>/` tfvars folder, run scripts with that env name |
| Add RAG to this journal app | Chroma locally + pgvector on RDS for AWS, DynamoDB Streams for indexing |
