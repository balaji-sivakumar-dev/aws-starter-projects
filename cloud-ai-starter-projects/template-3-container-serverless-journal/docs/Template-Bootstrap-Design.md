# Template Bootstrap Design — Using Template 3 as a Reusable Foundation

## Purpose

This document describes how to evolve Template 3 from a working journal app into a reusable bootstrap that anyone can use to start a new AI-enabled cloud application. It covers:

- What is already generic vs. what is hardcoded to "journal"
- The two bootstrapping approaches and trade-offs
- A concrete checklist of what to change when creating a new app
- The target state for a "true template" and the changes required

---

## Current State — What Is and Isn't Reusable

### Already fully generic (~70% of the codebase)

These components work for any app today without changes:

| Component | Why it's generic |
|-----------|-----------------|
| Cognito auth (PKCE, JWT) | All names driven by `app_prefix` + `env` variables |
| API Gateway (JWT authorizer, CORS, routes pattern) | Routes are config-driven; auth is domain-agnostic |
| CloudFront + S3 web hosting | Bucket/distribution names are fully parameterized |
| Step Functions async pattern | State machine ARN and Lambda ARN are both injected at deploy time |
| All Terraform module structure | `${var.app_prefix}-${var.env}-*` naming throughout |
| Setup/destroy scripts | Logic is env-driven; only default values reference "journal" |
| React app structure | Auth flow, API client, config — all generic |

### Hardcoded to "journal" (~30% needs changing)

An audit of the codebase found the following journal-specific elements:

#### Environment variable names (4 files)
The name `JOURNAL_TABLE_NAME` is hardcoded in:
- `services/lambda_api/src/handler.py`
- `services/workflows/src/ai_gateway.py`
- `infra/terraform/modules/compute_lambda/main.tf`
- `infra/terraform/modules/ai_gateway/main.tf`

#### DynamoDB table name
`infra/terraform/modules/db/main.tf` appends `-journal` as a literal suffix:
```hcl
name = "${var.app_prefix}-${var.env}-journal"
```

#### Data model entity types
`handler.py` uses `JOURNAL_ENTRY`, `ENTRY_LOOKUP`, `PERIOD_SUMMARY` as the SK prefixes — these are journal domain concepts.

#### API routes
Routes `/entries`, `/entries/{entryId}`, `/insights/summaries` are journal-specific. A task manager would use `/tasks`, a CRM would use `/contacts`.

#### AI prompt template
The prompt in `ai_gateway.py` assumes a `title + body` structure and asks for journal-style summaries and tags.

#### Frontend copy and branding
- App title: "Reflect" (hardcoded in `App.jsx`)
- Nav label: "📝 Journal"
- Auth screen: "Your AI-powered journal"
- Form label: "Journal Entry"

#### Script defaults
All three setup scripts default to `PROJECT_PREFIX="journal"` when the variable is not set.

#### Terraform state S3 key path
`step-2-bootstrap-terraform-backend.sh` hardcodes the S3 state path as:
```
template-3/container-serverless-journal/${ENV_NAME}/terraform.tfstate
```

---

## Approach 1 — Copy and Customise (Current Best Approach)

The simplest and most practical approach right now. No tooling required.

### How it works

1. Copy the template directory:
   ```bash
   cp -r template-3-container-serverless-journal my-new-app
   cd my-new-app
   ```

2. Follow the customisation checklist (see below).

3. Run the standard setup scripts — they provision a fully isolated AWS stack.

### Trade-offs

| Pro | Con |
|-----|-----|
| No tooling to build or maintain | Manual find-and-replace across ~10 files |
| Works today | No automated validation that all references were updated |
| Each app is fully independent | Template improvements must be backported manually |
| Easy to diverge and customise | No shared dependency on a common base |

### When to use

Use this approach when:
- You're starting one or two new apps
- The apps are significantly different in domain
- You don't need to keep in sync with template improvements

---

## Approach 2 — GitHub Template Repository (Recommended Next Step)

GitHub supports "Template repositories" — a repo marked as a template that anyone can instantiate with one click, creating a fresh copy with all history stripped.

### How it works

1. Mark the repo (or a clean branch/folder) as a GitHub Template repository.
2. Anyone clicks "Use this template" → enters their app name → gets a fresh copy.
3. A setup script (or GitHub Actions workflow) runs automatically to rename references.

### What a setup script would do

A script like `scripts/init-new-app.sh <AppName> <app_prefix>` would:

1. Replace all occurrences of `journal` (the suffix, not the brand) with the new `app_prefix`:
   - `JOURNAL_TABLE_NAME` → `${APP_PREFIX_UPPER}_TABLE_NAME`
   - `journal-dev-*` default → `${app_prefix}-dev-*`
   - DynamoDB table suffix `-journal` → `-${app_prefix}`
2. Replace UI copy:
   - "Reflect" → new app name
   - "Journal" nav label → new entity name
   - "Journal Entry" form label → new entity name
3. Update Terraform state S3 key path to use the new app name.
4. Update `dev.tfvars.example` default `app_prefix`.

### What it would NOT do

The script cannot automatically replace domain logic:
- API routes (`/entries`) — the developer decides what their entities are
- Data model (PK/SK patterns) — depends on the domain
- AI prompt — depends on what the app is doing with AI
- Frontend components — the React UI needs to be rebuilt for the new domain

These are documented in the customisation checklist.

### Trade-offs

| Pro | Con |
|-----|-----|
| One-click bootstrap | Requires writing and maintaining the init script |
| Automated renaming reduces mistakes | Still requires manual domain logic changes |
| Clear separation of "plumbing" vs "domain" | GitHub template repos don't update from source — still no shared base |
| Good for sharing publicly | |

### When to use

Use this approach when:
- You want to share the template with a team or publicly
- You expect to create several apps from it
- You want a polished onboarding experience

---

## Approach 3 — Terraform Module Registry + App Shell (Future / Advanced)

The most engineering-intensive but most maintainable long-term approach. Separate the infrastructure modules from the application code.

### How it works

```
terraform-modules-registry/        ← shared, versioned Terraform modules
  modules/auth/
  modules/db/
  modules/api_edge/
  modules/web_hosting/
  modules/workflow/
  modules/ai_gateway/

my-app-1/                          ← new app, references registry modules
  infra/terraform/main.tf          ← calls registry modules by version
  services/                        ← own business logic
  apps/web/                        ← own React app

my-app-2/                          ← another new app
  ...
```

In `my-app-1/infra/terraform/main.tf`:
```hcl
module "auth" {
  source  = "git::https://github.com/your-org/terraform-modules.git//auth?ref=v1.2.0"
  ...
}
```

### Trade-offs

| Pro | Con |
|-----|-----|
| All apps benefit from infra improvements | Significant upfront engineering |
| Semantic versioning of infrastructure | Module API must be stable and backwards-compatible |
| Clear separation of infrastructure vs. domain | Requires a module registry (GitHub or Terraform Registry) |
| No copy-paste sprawl | Cross-app testing and versioning discipline required |

### When to use

Use this approach when:
- You have 5+ apps sharing the same infrastructure patterns
- You have a dedicated platform/infrastructure team
- You need to roll out security patches across all apps consistently

---

## Recommended Path

| Now | Next | Later |
|-----|------|-------|
| Copy and customise (works today) | GitHub Template repo with `init-new-app.sh` | Terraform module registry |
| Use the checklist below | Automated renaming for "plumbing" references | Versioned shared modules |

---

## Customisation Checklist (for Any New App)

When copying Template 3 for a new app, work through these in order:

### 1 — Rename plumbing references (find-and-replace, ~15 min)

| What to change | From | To | Files affected |
|---------------|------|----|----------------|
| Env var name | `JOURNAL_TABLE_NAME` | `<APP>_TABLE_NAME` | handler.py, ai_gateway.py, 2 tf modules |
| DynamoDB table suffix | `-journal` | `-<app_prefix>` | modules/db/main.tf |
| Script defaults | `PROJECT_PREFIX="journal"` | `PROJECT_PREFIX="<app_prefix>"` | 3 setup scripts |
| S3 state key path | `container-serverless-journal` | `<new-app-folder-name>` | step-2 script |
| Terraform variable name | `journal_table_arn/name` | `table_arn/name` | compute_lambda, ai_gateway modules + root main.tf |

### 2 — Update app branding in the frontend (~10 min)

| File | What to change |
|------|----------------|
| `apps/web/src/App.jsx` | App title ("Reflect"), auth screen subtitle, nav label ("Journal") |
| `apps/web/src/components/EntryForm.jsx` | Form label ("Journal Entry") |
| `apps/web/src/styles.css` | Page title / favicon references if any |

### 3 — Define your data model (domain work, ~1–2 hrs)

Replace journal entity types with your domain:

| Journal concept | Replace with |
|----------------|-------------|
| `JOURNAL_ENTRY` entity type | Your entity (e.g., `TASK`, `POST`, `CONTACT`) |
| `ENTRY#{ts}#{id}` SK pattern | `<ENTITY>#{ts}#{id}` |
| `ENTRYID#{id}` lookup SK | `<ENTITY>ID#{id}` |
| `PERIOD_SUMMARY` entity | Your aggregation concept (or remove if not needed) |
| Fields: `title`, `body`, `aiStatus`, `summary`, `tags` | Your fields |

### 4 — Replace API routes and handler logic (domain work, ~2–4 hrs)

In `infra/terraform/main.tf` replace `api_routes`:
```hcl
# Replace journal routes with your domain routes
list_items  = { route_key = "GET /items",          authorization = "JWT" }
create_item = { route_key = "POST /items",         authorization = "JWT" }
get_item    = { route_key = "GET /items/{itemId}", authorization = "JWT" }
# ... etc.
```

In `services/lambda_api/src/handler.py`:
- Replace route handlers with your business logic
- Replace DynamoDB access patterns with your entity model
- Keep the `get_claims()`, auth checking, and `response()`/`error()` helpers — those are generic

### 5 — Rewrite the AI prompt (domain work, ~30 min)

In `services/workflows/src/ai_gateway.py`, replace the prompt and result parsing:
```python
# Replace with your domain's AI task
prompt = (
    "Your task-specific prompt here.\n"
    f"input: {item.get('your_field', '')}"
)
# Update result parsing to match your expected output schema
```

### 6 — Rebuild the React UI (domain work, varies)

The React plumbing (auth flow, API client, config) is fully reusable.
Replace these domain-specific components:
- `components/EntryList.jsx` → your item list
- `components/EntryDetail.jsx` → your item detail view
- `components/EntryForm.jsx` → your create/edit form
- `components/InsightsPanel.jsx` → your analytics/summary view (or remove)

Keep these unchanged:
- `auth/auth.js`, `auth/pkce.js` — generic OAuth 2.0 PKCE
- `api/client.js` — generic HTTP client with auth headers
- `config.js` — reads from `.env`, fully generic

### 7 — Update dev.tfvars

```hcl
app_prefix = "<your-app-name>"   # drives all AWS resource names
env        = "dev"
aws_region = "ca-central-1"
```

### 8 — Run setup

```bash
AWS_PROFILE=<your-profile> ./scripts/setup/step-2-bootstrap-terraform-backend.sh dev
AWS_PROFILE=<your-profile> ./scripts/setup/step-3a-terraform-apply.sh dev
AWS_PROFILE=<your-profile> ./scripts/setup/step-4a-deploy-web-to-s3.sh dev
```

---

## What a "True Template" Looks Like (Target State)

If we were to make this a first-class template, the main structural change is:

**Replace all `journal`-specific variable names with generic names.**

| Current | Target (generic) |
|---------|-----------------|
| `JOURNAL_TABLE_NAME` env var | `TABLE_NAME` or `PRIMARY_TABLE_NAME` |
| `journal_table_arn` Terraform variable | `table_arn` |
| `journal_table_name` Terraform variable | `table_name` |
| DynamoDB: `${app_prefix}-${env}-journal` | `${app_prefix}-${env}-data` or `${app_prefix}-${env}` |
| Default `app_prefix = "journal"` | No default — require it |
| `PROJECT_PREFIX="journal"` in scripts | Require as env var, print error if not set |

With these changes, a new developer could use the template without needing to do a find-and-replace for "journal". They would only need to:
1. Set `app_prefix` in tfvars
2. Write their domain handler logic
3. Build their React UI

The infrastructure, auth, async AI pattern, and deployment pipeline would all work without any modification.

---

## Summary

Template 3 is **~70% reusable today** as a copy-and-customise template. The 30% that needs changing is clearly bounded:

- **15 minutes** of mechanical find-and-replace for "journal" in infrastructure/config files
- **Domain work** (data model, routes, AI prompt, React UI) that no template can do for you — it depends entirely on what the new app does

The most impactful single improvement to make it a true bootstrap template is renaming `JOURNAL_TABLE_NAME` and the DynamoDB table suffix to be generic. That alone removes the most confusing "journal-specific" artefact from a new app's infrastructure.
