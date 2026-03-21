# Reusable Template Plan

> Extract Template 3 (Reflect) into a generic AWS starter template that can bootstrap
> new full-stack apps in minutes. First consumer: **Budget App** migration.

---

## Status: DRAFT — awaiting review

---

## 1. Problem

Every new project rebuilds the same plumbing: Cognito auth, DynamoDB single-table,
Lambda/API Gateway, CloudFront hosting, Step Functions AI workflow, local Docker
Compose stack, Makefile, deploy scripts. Template 3 has all of this production-tested
but it's tightly coupled to the "journal" domain.

---

## 2. Goal

```
make new-project APP=budget
# -> creates template-budget/ with:
#    - working local dev stack (docker compose up)
#    - working AWS deploy (make deploy)
#    - placeholder CRUD for a single entity
#    - Cognito auth wired end-to-end
#    - AI enrichment pipeline (opt-in)
#    - RAG pipeline (opt-in)
#    - Admin dashboard (opt-in)
#    - CSV import (opt-in)
```

A developer should go from `make new-project` to a running app in < 30 minutes.

---

## 3. What the Template Provides (Batteries Included)

### 3a. Infrastructure (keep as-is, parameterize names)

| Layer | What | Template Variable |
|-------|------|----|
| Auth | Cognito User Pool + PKCE + pre-signup Lambda allowlist | `APP_PREFIX` |
| Database | DynamoDB single-table (PK/SK) with auto-create | `APP_PREFIX`, `TABLE_NAME` |
| Compute | Lambda + API Gateway v2 (HTTP API, JWT auth) | `APP_PREFIX` |
| Hosting | S3 + CloudFront (OAC) for React SPA | `APP_PREFIX` |
| AI Workflow | Step Functions + Lambda AI Gateway | `APP_PREFIX` |
| AI Models | Bedrock (Titan Embed + Nova Lite), optional Groq | `BEDROCK_REGION` |
| Secrets | SSM Parameter Store (API keys, user allowlist) | `APP_PREFIX` |
| Observability | CloudWatch Logs + Traces | automatic |
| State backend | S3 + DynamoDB lock table for Terraform | `APP_PREFIX` |

### 3b. Application Code (generalize)

| Layer | Current (Journal) | Template Version |
|-------|-------------------|------------------|
| **API core** | `handlers.py` with entry CRUD + insights | Generic CRUD handler for a single "Item" entity |
| **Models** | `JournalEntry`, `PeriodSummary` | `BaseItem` with `user_id`, `item_id`, `created_at`, `data` (JSON) |
| **Repository** | DynamoDB single-table with entry/summary patterns | Same pattern, parameterized entity prefix |
| **Auth** | Cognito JWT + local bypass | Same (no change needed) |
| **LLM** | `enrich()` + `analyze_period()` | `enrich(item)` — prompt is project-specific |
| **RAG** | Bedrock Titan embeddings + DynamoDB vector store | Same (opt-in module) |
| **Web UI** | Journal-specific components | Shell app: nav, auth, dashboard, single entity CRUD |
| **Admin** | Audit log, user filter | Same (opt-in) |
| **CSV Import** | Journal CSV columns | Generic CSV importer (column mapping config) |

### 3c. Tooling (keep as-is)

| Tool | Status |
|------|--------|
| Makefile | Keep — parameterize `APP_PREFIX`, `ENV`, `PROFILE` |
| Shell scripts | Keep — already use `$1` for env |
| Docker Compose | Keep — rename containers from `t3-*` to `${APP}-*` |
| draw.io MCP | Keep `make drawio` target |
| pytest suite | Keep — tests for generic CRUD + auth + LLM |

---

## 4. Extraction Steps (Template 3 → Base Template)

### Phase 1: Parameterize Template 3 (in-place refactor)

No new directory yet. Make Template 3 itself driven by config so the extraction
is mechanical.

| # | Task | Files |
|---|------|-------|
| 1.1 | Replace all hardcoded `"journal"` with `APP_PREFIX` env var in Python code | `repository.py`, `handlers.py`, `models.py` |
| 1.2 | Replace `t3-` container prefixes with `${APP_PREFIX:-app}` in docker-compose | All `docker-compose*.yml` |
| 1.3 | Replace `"template-3-journal-web"` in `package.json` with generic name | `apps/web/package.json` |
| 1.4 | Make `<title>` in `index.html` read from `VITE_APP_NAME` env var | `apps/web/index.html`, `config.js` |
| 1.5 | Terraform: ensure `app_prefix` variable flows to every resource name | All `modules/*/main.tf` |
| 1.6 | Scripts: replace any hardcoded `journal` references | `scripts/setup/*.sh` |
| 1.7 | Verify: `APP_PREFIX=reflect make dev` still works | Manual test |

**Estimated effort:** 1 session

### Phase 2: Create the Base Template

Copy Template 3 into a new `_base-template/` directory, strip domain-specific code.

```
cloud-ai-starter-projects/
  _base-template/               <-- NEW
    apps/web/                   # Shell React app
    services/api/               # Generic CRUD API
    services/lambda_api/        # Lambda wrapper
    services/workflows/         # AI Gateway
    infra/terraform/            # All modules
    scripts/                    # Setup + destroy
    docs/                       # Architecture template
    docker-compose.yml
    Makefile
    README.md
    template.json               <-- NEW: template metadata
```

**`template.json`** — drives the bootstrap script:
```json
{
  "variables": {
    "APP_PREFIX": { "prompt": "App name (lowercase, no spaces)", "default": "myapp" },
    "APP_TITLE": { "prompt": "Display name", "default": "My App" },
    "AWS_REGION": { "prompt": "AWS region", "default": "ca-central-1" },
    "AWS_PROFILE": { "prompt": "AWS CLI profile", "default": "default" },
    "ENABLE_AI": { "prompt": "Enable AI enrichment? (y/n)", "default": "y" },
    "ENABLE_RAG": { "prompt": "Enable RAG pipeline? (y/n)", "default": "y" },
    "ENABLE_ADMIN": { "prompt": "Enable admin dashboard? (y/n)", "default": "y" },
    "ENABLE_CSV_IMPORT": { "prompt": "Enable CSV import? (y/n)", "default": "y" }
  },
  "features": {
    "ai": { "dirs": ["services/workflows"], "terraform_modules": ["ai_gateway", "workflow"] },
    "rag": { "dirs": ["services/api/src/rag"], "terraform_modules": [] },
    "admin": { "files": ["services/api/src/adapters/fastapi/admin_routes.py", "apps/web/src/components/AdminPanel.jsx"] },
    "csv_import": { "files": ["apps/web/src/components/ImportCSV.jsx"] }
  }
}
```

**Estimated effort:** 2 sessions

### Phase 3: Bootstrap Script

```bash
# scripts/new-project.sh
# Usage: ./scripts/new-project.sh budget
# Creates: cloud-ai-starter-projects/template-budget/
```

The script:
1. Reads `template.json` variables (interactive prompts or `--defaults` flag)
2. Copies `_base-template/` → `template-{APP_PREFIX}/`
3. Finds/replaces placeholder strings (`{{APP_PREFIX}}`, `{{APP_TITLE}}`, etc.)
4. Removes opt-out features (if `ENABLE_AI=n`, removes `services/workflows/`, etc.)
5. Generates `.env.local`, `.env.docker`, `.env.users.example` with correct values
6. Generates `terraform.tfvars.example` with correct defaults
7. Runs `cd apps/web && npm install`
8. Prints next steps

Also add a `make new-project APP=budget` target at the repo-root Makefile.

**Estimated effort:** 1 session

### Phase 4: Validate with Budget App Migration

See Section 6 below.

---

## 5. Base Template — Entity Model

The template ships with a single generic "Item" entity to demonstrate the full
CRUD + AI + RAG pipeline. Projects replace/extend this with their domain models.

### DynamoDB Key Schema (same single-table pattern)

```
PK: USER#{userId}
SK: ITEM#{createdAt}#{itemId}        # main item
SK: ITEMID#{itemId}                  # lookup by ID
SK: SUMMARY#{createdAt}#{summaryId}  # AI-generated summary
SK: VECTOR#{itemId}                  # RAG embedding
SK: CONVERSATION#{conversationId}    # RAG chat history
SK: AUDIT#{timestamp}#{action}       # Admin audit log
```

### Generic Item Model

```python
@dataclass
class Item:
    user_id: str
    item_id: str
    title: str
    body: str               # main content
    data: dict              # flexible JSON for domain-specific fields
    created_at: str
    updated_at: str
    ai_status: str          # NONE | QUEUED | DONE | ERROR
    ai_summary: str | None
    ai_tags: list[str]
```

Projects extend by:
1. Adding fields to `data` dict (no schema migration needed)
2. Or replacing `Item` with domain model(s) and updating `repository.py` + `handlers.py`

---

## 6. Budget App Migration Plan

### 6a. Current Budget App Architecture

| Layer | Current | Notes |
|-------|---------|-------|
| Backend | SAM (6 Lambda functions) | Python, handler per resource |
| Frontend | React 19 + TypeScript + Vite | Tabs: Transactions, Accounts, Categories, Rules, Mappings |
| Database | DynamoDB single-table | PK=`USER#{userId}`, SK by entity type |
| Auth | Cognito (CDK stack) | PKCE + hosted UI |
| IaC | SAM `template.yaml` + CDK (TypeScript) | Two separate stacks |
| Local dev | SAM Local + DynamoDB Docker | `make local-clean-start` |

### 6b. What Aligns Well (low effort)

| Feature | Template Has | Budget App Needs | Effort |
|---------|-------------|-----------------|--------|
| Cognito PKCE auth | ✅ | ✅ Same | Copy |
| DynamoDB single-table | ✅ | ✅ Same pattern, different entities | Map SK prefixes |
| CloudFront + S3 hosting | ✅ | ✅ Needs this (currently missing) | Copy |
| Docker Compose local dev | ✅ | ✅ (currently SAM Local) | Copy |
| Makefile | ✅ | ✅ Already has one | Merge |
| CSV import | ✅ | ✅ Core feature | Adapt columns |
| API Gateway + Lambda | ✅ | ✅ Same | Copy |
| Deploy scripts | ✅ | ❌ Uses SAM CLI | Replace SAM with Terraform |

### 6c. What Needs Adaptation (medium effort)

| Feature | Template Has | Budget App Needs | Effort |
|---------|-------------|-----------------|--------|
| Single entity CRUD | `entries` only | 5 entities: transactions, accounts, categories, category_rules, mappings | Add entity routes |
| Repository | Single entity repo | 5 repos (already written in `packages/adapters/`) | Port repos |
| Domain models | `JournalEntry` | `Transaction`, `Account`, `Category`, `CategoryRule`, `MappingRule` | Port models |
| CSV import | Generic columns | Institution-specific header mapping + sign normalization | Adapt parser |
| Validation | Basic | Amount parsing, sign normalization, duplicate detection | Port from `packages/domain/validation.py` |

### 6d. What to Drop or Defer

| Feature | Decision | Reason |
|---------|----------|--------|
| SAM template.yaml | **Drop** | Replace with Terraform (template standard) |
| CDK auth stack | **Drop** | Replace with Terraform auth module |
| AI enrichment | **Defer** | Budget app doesn't need AI yet |
| RAG pipeline | **Defer** | Not applicable to budget tracking |
| Insights (period summaries) | **Defer** | Could add later for spending analysis |
| Step Functions | **Defer** | No async workflow needed initially |

### 6e. Migration Steps

```
1. Bootstrap
   make new-project APP=budget
   # Answer prompts:
   #   APP_TITLE = "Budget Tracker"
   #   ENABLE_AI = n
   #   ENABLE_RAG = n
   #   ENABLE_ADMIN = y  (for multi-user visibility)
   #   ENABLE_CSV_IMPORT = y

2. Port Domain Models
   - Copy budget-app/packages/domain/models.py → services/api/src/core/models.py
   - Adapt to Pydantic (from dataclasses)
   - Port validation.py

3. Port Repositories
   - Copy budget-app/packages/adapters/*.py → services/api/src/core/
   - Update DynamoDB key patterns to match template convention
   - Port tests

4. Port API Routes
   - Map SAM handlers to FastAPI routes:
     transactions_handler → routes/transactions.py
     accounts_handler    → routes/accounts.py
     categories_handler  → routes/categories.py
     category_rules      → routes/category_rules.py
     mappings            → routes/mappings.py
   - Add bootstrap endpoint (GET /bootstrap → returns all config in one call)

5. Port Frontend
   - Copy React components from budget-app/apps/web/client/src/
   - Replace SAM Local API client with template's api/client.js
   - Wire Cognito auth (already in template)
   - Keep TypeScript (template uses JSX but TS is fine with Vite)

6. Port CSV Import
   - Adapt ImportCSV.jsx for budget CSV columns
   - Wire PapaParse (budget app already uses it)
   - Port header mapping logic
   - Port sign normalization + duplicate detection

7. Update Terraform
   - Only modules needed: auth, db, compute_lambda, api_edge, web_hosting
   - Remove: ai_gateway, workflow (AI disabled)
   - Update variables.tf with budget-specific defaults

8. Test
   - Port existing pytest suite
   - Run make test
   - Run make dev → verify local stack
   - Deploy: make deploy

9. Cleanup
   - Remove template placeholder files
   - Update README, Architecture.md, Setup.md
   - Archive old budget-app SAM/CDK code
```

**Estimated effort:** 3-4 sessions

---

## 7. Improvements to Template 3 Before Extraction

These should be done on Template 3 (Reflect) first, then carried into the base template.

### 7a. Required (blockers for reuse)

| # | Improvement | Why |
|---|------------|-----|
| R1 | Remove all hardcoded `"journal"` from Python code — use `TABLE_NAME` env var everywhere | Template must be name-agnostic |
| R2 | Make Docker container names use `${COMPOSE_PROJECT_NAME}` (Docker Compose built-in) instead of `t3-*` | Avoids conflicts when running multiple projects |
| R3 | Extract prompt templates from handler code into `prompts/` directory | Projects need different AI prompts |
| R4 | Split `handlers.py` (currently 500+ lines) into per-entity handler files | Template consumers shouldn't wade through journal-specific logic |

### 7b. Recommended (quality-of-life)

| # | Improvement | Why |
|---|------------|-----|
| Q1 | Add `make lint` target (ruff for Python, eslint for JS) | Every project needs linting |
| Q2 | Add `make format` target (ruff format + prettier) | Consistent code style |
| Q3 | Add GitHub Actions CI workflow (test + lint on PR) | CI from day one |
| Q4 | Add health check endpoint that verifies DynamoDB connectivity | Currently `/health` just returns 200 |
| Q5 | Add `SEED_DATA=true` env var to auto-seed on first `docker compose up` | Faster onboarding |
| Q6 | Move from `vite.config.js` proxy to Nginx proxy for local dev parity | Local and deployed routing should match |

### 7c. Future (nice-to-have)

| # | Improvement | Why |
|---|------------|-----|
| F1 | Container compute option (App Runner) as opt-in module | Template 4's original purpose |
| F2 | GitHub Template Repository integration | `Use this template` button on GitHub |
| F3 | Pulumi alternative to Terraform | Some teams prefer Pulumi |
| F4 | Multi-tenant support (org-level PK prefix) | Enterprise use cases |

---

## 8. Directory Structure After Extraction

```
aws-starter-projects/
  cloud-ai-starter-projects/
    _base-template/                     # ← The reusable template
      template.json                     # Bootstrap config + feature flags
      Makefile
      README.md
      docker-compose.yml
      docker-compose.ollama.yml
      .env.docker
      .env.local.example
      .env.users.example
      apps/
        web/                            # React shell (auth, nav, single entity CRUD)
      services/
        api/                            # FastAPI + generic Item CRUD
        lambda_api/                     # Lambda wrapper
        workflows/                      # [opt-in] AI Gateway
      infra/
        terraform/
          modules/                      # All 8 modules
          environments/
      scripts/
        setup/
        destroy/
        new-project.sh                  # ← Bootstrap script
      docs/
        Architecture-Template.md
        Setup-Template.md

    template-3-container-serverless-journal/   # Reflect (unchanged, still works)
    template-budget/                           # Budget App (generated from template)
    template-4-container-journal/              # (future)
```

---

## 9. Execution Order

| Phase | What | Depends On | Sessions |
|-------|------|-----------|----------|
| **1** | Parameterize Template 3 | — | 1 |
| **2** | Create `_base-template/` | Phase 1 | 2 |
| **3** | Bootstrap script (`new-project.sh`) | Phase 2 | 1 |
| **4** | Migrate Budget App | Phase 3 | 3–4 |
| **Total** | | | **7–8 sessions** |

---

## 10. Open Questions

1. **TypeScript or JavaScript for the base template web app?**
   - Template 3 uses JSX. Budget app uses TSX.
   - Recommendation: Keep JSX in template (simpler), let projects upgrade to TS if needed.

2. **Should the base template include the Insights (period summary) feature?**
   - It's generic enough (summarize items over a time range) to be useful across projects.
   - Recommendation: Include as opt-in, like AI enrichment.

3. **Should we keep the container compute option (App Runner) in the base template?**
   - Template 3 supports `compute_mode = "serverless" | "container" | "hybrid"`.
   - Recommendation: Base template = serverless only. Container as a separate template or opt-in module.

4. **Where should the base template live?**
   - Option A: `_base-template/` in this repo (current plan)
   - Option B: Separate GitHub repo with "Use this template" button
   - Recommendation: Start with A, graduate to B when stable.

5. **Should the bootstrap script be a shell script or a Python CLI?**
   - Shell is simpler, Python allows richer prompting and validation.
   - Recommendation: Shell script. Keep it simple.
