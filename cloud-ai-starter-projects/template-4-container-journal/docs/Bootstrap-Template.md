# Bootstrap Template — GitHub Template Repo Design

> **Status: Design phase**
> Last updated: 2026-03-14

---

## 1. The problem

Every new app (Curriculum, Budget, Tax, Family Tree) needs the same base layers:
- Cognito auth + PKCE flow
- DynamoDB single-table setup
- Lambda API with routing
- API Gateway with JWT auth
- S3 + CloudFront hosting
- Docker Compose local dev
- Setup/destroy scripts

Rebuilding these from scratch each time is wasteful. Copying Template 3 and deleting journal-specific code is error-prone.

**Solution**: Convert this repo into a **GitHub Template Repository** with a bootstrap script that scaffolds a new app with only the layers you need.

---

## 2. How GitHub Template Repos work

1. Mark the repo as a template (Settings → Template repository checkbox)
2. Others click **"Use this template"** → creates a new repo with the same files (no git history)
3. A bootstrap script in the new repo customizes it (rename, select features, delete unused modules)

This is simpler than Cookiecutter or Yeoman — no external tools needed.

---

## 3. Feature tags — pick what you need

The bootstrap script lets you select which capabilities to include:

```
┌─────────────────────────────────────────────────┐
│           PLATFORM BOOTSTRAP                     │
│                                                  │
│  App name: curriculum-platform                   │
│  AWS region: ca-central-1                        │
│                                                  │
│  Select features:                                │
│  ✅ [core]     Auth + DB + API + Web hosting     │
│  ✅ [ai]       LLM provider abstraction          │
│  ☐  [rag]      Embedding + vector store          │
│  ☐  [files]    S3 upload + processing pipeline   │
│  ✅ [workflow]  Step Functions async tasks        │
│  ☐  [billing]  Usage tracking + Stripe hooks     │
│                                                  │
│  Compute mode:                                   │
│  ● Lambda (serverless)                           │
│  ○ Container (App Runner)                        │
│  ○ Both (hybrid)                                 │
└─────────────────────────────────────────────────┘
```

### Feature dependency map

```
core ← required (auth, db, api, web)
  │
  ├── ai ← optional (LLM providers, prompts)
  │    │
  │    ├── rag ← optional (requires ai)
  │    │
  │    └── workflow ← optional (Step Functions, async AI tasks)
  │
  ├── files ← optional (S3 upload, processing pipeline)
  │
  └── billing ← optional (usage metering, subscription hooks)
```

---

## 4. What the bootstrap script does

```bash
./bootstrap.sh
```

1. **Prompts** for app name, region, feature tags
2. **Renames** all `journal` / `reflect` references → your app name
3. **Deletes** unused feature modules:
   - No `[rag]`? → removes `modules/rag/`, `domains/rag/`, `docker-compose.rag.yml`
   - No `[files]`? → removes `modules/file_processing/`, S3 upload routes
   - No `[ai]`? → removes `modules/ai_gateway/`, `modules/workflow/`, LLM providers
4. **Updates** Terraform `main.tf` to only include selected modules
5. **Updates** `docker-compose.yml` to only include selected services
6. **Generates** `dev.tfvars.example` with relevant variables
7. **Prints** next steps (run setup scripts)

### Example output:

```
✓ Created curriculum-platform
✓ Features: core, ai, workflow
✓ Skipped: rag, files, billing
✓ Compute: lambda (serverless)

Next steps:
  1. cd curriculum-platform
  2. Review infra/terraform/environments/dev/dev.tfvars.example
  3. ./scripts/setup/step-1-aws-configure.md
  4. ./scripts/setup/step-2-bootstrap-terraform-backend.sh dev
```

---

## 5. Template repo structure

```
aws-app-template/                     ← GitHub Template Repo
├── bootstrap.sh                      ← Interactive scaffolding script
├── bootstrap.config.example          ← Non-interactive config file
│
├── platform/                         ← Shared infrastructure (always included)
│   ├── auth/                         ← Cognito JWT validation + local bypass
│   │   ├── auth.py
│   │   └── pkce.js
│   ├── db/                           ← DynamoDB repository base class
│   │   └── repository.py
│   ├── api/                          ← API client, error handling, middleware
│   │   ├── middleware.py
│   │   └── response.py
│   └── config/                       ← Environment config loader
│       └── config.py
│
├── domains/                          ← App-specific (starts with example domain)
│   └── _example/                     ← Renamed by bootstrap script
│       ├── handlers.py               ← Business logic (CRUD example)
│       ├── models.py                 ← Pydantic models
│       ├── repository.py             ← DynamoDB access (extends base)
│       └── routes.py                 ← FastAPI router
│
├── features/                         ← Optional feature modules
│   ├── ai/                           ← [ai] tag
│   │   ├── llm/
│   │   │   ├── interface.py
│   │   │   ├── factory.py
│   │   │   └── providers/
│   │   └── prompts/
│   │       └── _example_prompt.py
│   ├── rag/                          ← [rag] tag
│   │   ├── embedding/
│   │   ├── retriever.py
│   │   ├── vector_store/
│   │   └── routes.py
│   ├── files/                        ← [files] tag
│   │   ├── upload.py
│   │   ├── processors/
│   │   └── routes.py
│   ├── workflow/                     ← [workflow] tag
│   │   ├── task_router.py
│   │   └── statemachine/
│   └── billing/                      ← [billing] tag
│       ├── usage.py
│       └── routes.py
│
├── adapters/                         ← Deployment wiring
│   ├── lambda_handler.py             ← Fat Lambda entry point
│   ├── fastapi_app.py                ← FastAPI factory (container)
│   └── mangum_handler.py             ← FastAPI via Mangum (Lambda)
│
├── apps/web/                         ← React frontend shell
│   ├── src/
│   │   ├── App.jsx                   ← Configurable nav shell
│   │   ├── auth/                     ← Cognito PKCE (reusable)
│   │   ├── api/                      ← API client (reusable)
│   │   └── components/
│   │       └── _ExamplePage.jsx      ← Starter component
│   └── ...
│
├── infra/terraform/
│   ├── main.tf                       ← Module composition (features toggled)
│   ├── variables.tf
│   └── modules/
│       ├── auth/                     ← [core]
│       ├── db/                       ← [core]
│       ├── compute_lambda/           ← [core] if lambda mode
│       ├── compute_container/        ← [core] if container mode
│       ├── api_edge/                 ← [core]
│       ├── web_hosting/              ← [core]
│       ├── ai_gateway/              ← [ai] + [workflow]
│       ├── workflow/                 ← [workflow]
│       ├── rag/                      ← [rag]
│       └── file_storage/            ← [files]
│
├── scripts/
│   ├── setup/                        ← Numbered steps (parameterized)
│   └── destroy/
│
├── docker-compose.yml                ← Base (API + DynamoDB Local + Web)
├── docker-compose.ollama.yml         ← [ai] overlay
├── docker-compose.groq.yml           ← [ai] overlay
├── docker-compose.rag.yml            ← [rag] overlay
│
└── docs/
    ├── Architecture.md
    └── Setup.md
```

---

## 6. Adding features later

You skipped `[rag]` at bootstrap? You can add it later:

```bash
./bootstrap.sh --add-feature rag
```

This:
1. Copies `features/rag/` into your project
2. Adds `module "rag"` block to `main.tf`
3. Adds RAG routes to your API router
4. Adds `docker-compose.rag.yml` overlay
5. Updates `dev.tfvars.example` with RAG-related variables

The feature modules are designed to be **additive** — they plug into the existing API, Terraform, and Docker Compose without modifying existing code.

---

## 7. How this applies to the Curriculum app

```bash
# Step 1: Create from template
gh repo create curriculum-platform --template balaji-sivakumar-dev/aws-app-template

# Step 2: Bootstrap with selected features
cd curriculum-platform
./bootstrap.sh \
  --name curriculum-platform \
  --region ca-central-1 \
  --features core,ai,rag,workflow,files \
  --compute lambda

# Step 3: You get this structure, ready to build on
domains/
├── _example/     ← rename to content/, exams/, learning/, etc.

# Step 4: Start building domain logic
# The auth, DB, API, LLM, RAG, file upload layers are all wired and working
```

**What you build** (app-specific):
- `domains/content/` — course + module CRUD
- `domains/exams/` — exam generation, grading, scoring
- `domains/learning/` — performance analytics, recommendations
- Custom LLM prompts in `features/ai/prompts/`
- RAG chunking strategy for course materials

**What you don't build** (platform provides):
- Auth flow (Cognito PKCE + local bypass)
- DynamoDB setup + base repository class
- API Gateway + JWT authorizer
- LLM provider abstraction
- RAG pipeline (embedding, storage, retrieval)
- File upload (pre-signed URLs + S3 events)
- Step Functions async task runner
- CloudFront + S3 hosting
- Docker Compose local dev
- Setup/destroy scripts

---

## 8. Priority order

Given the stated priorities:

| # | Project | Priority | Template features needed |
|---|---------|----------|------------------------|
| 1 | **Curriculum Platform** | High | core, ai, rag, workflow, files |
| 2 | **Budget Tracker** | Low (exists without AI) | core, ai, files (add RAG later) |
| 3 | **Tax Processor** | Hobby | core, ai, rag, files |
| 4 | **Family Tree** | Hobby | core, files |

### Recommended build order:

1. **Build the template repo** — extract reusable layers from Template 3
2. **Bootstrap the Curriculum app** — first consumer of the template
3. **Build Curriculum domain logic** — the app-specific parts
4. **Retrofit Budget Tracker** — migrate existing app onto the template, add AI/RAG
5. **Tax & Family Tree** — build when time allows, using the same template

The Curriculum app is the ideal first consumer because it exercises the most features (AI, RAG, file upload, async workflows). If the template supports Curriculum, it supports everything.

---

## 9. Build plan for the template repo

### Step 1 — Extract platform from Template 3
- Pull out auth, db, api middleware, config into `platform/`
- Pull out LLM providers into `features/ai/`
- Pull out Step Functions into `features/workflow/`
- Create `_example` domain with basic CRUD

### Step 2 — Add new features
- `features/rag/` — embedding + vector store + retrieval
- `features/files/` — S3 pre-signed upload + processing pipeline

### Step 3 — Build bootstrap script
- Interactive prompts for app name, region, features
- File manipulation (rename, delete, update `main.tf`)
- `--add-feature` support for incremental additions

### Step 4 — Test with Curriculum app
- Bootstrap → build domains → deploy → validate
- Feed issues back into the template

---

## 10. Open decisions

| Decision | Options | Leaning |
|----------|---------|---------|
| Template repo location | Same repo (`template-4/`) vs separate repo | **Separate repo** (`aws-app-template`) — cleaner for GitHub template feature |
| Bootstrap tool | Bash script vs Python script vs Cookiecutter | **Bash script** — no dependencies, works everywhere |
| Platform code sharing | Copy into each app vs Git submodule vs published package | **Copy** initially — simplest, no version management overhead. Publish as package later if maintaining 3+ apps |
| Frontend framework | React (current) vs Next.js vs plain HTML | **React** (current) — proven, works, no reason to change |
| Test framework | pytest (current) vs other | **pytest** — proven, keep it |
