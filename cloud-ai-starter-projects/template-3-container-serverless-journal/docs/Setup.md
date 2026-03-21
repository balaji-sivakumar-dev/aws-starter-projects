# Setup Guide — Reflect (Template 3)

## Local development (Docker)

Everything runs as containers — no local Python or Node install needed.

### Prerequisites

| Tool | Notes |
|------|-------|
| Docker Desktop 4.x+ | https://docs.docker.com/get-docker/ |
| Docker Compose v2 | Bundled with Docker Desktop |

### Start

```bash
git clone https://github.com/balaji-sivakumar-dev/aws-starter-projects.git
cd aws-starter-projects/cloud-ai-starter-projects/template-3-container-serverless-journal

make dev
# Web UI  → http://localhost:3000
# API     → http://localhost:8080/docs
```

Three containers start in dependency order:

| Container | Role | Port |
|-----------|------|------|
| `t3-dynamodb` | DynamoDB Local (in-memory) | 8000 |
| `t3-api` | Python FastAPI | 8080 |
| `t3-web` | React + Nginx | 3000 |

The UI runs in **local mode** — no login required (all requests use `dev-user`).

### Call the API directly

```bash
# Health
curl http://localhost:8080/health

# Create an entry
curl -s -X POST http://localhost:8080/entries \
  -H "Content-Type: application/json" \
  -H "X-User-Id: dev-user" \
  -d '{"title": "First entry", "body": "Hello journal!"}' | jq

# List entries
curl -s http://localhost:8080/entries -H "X-User-Id: dev-user" | jq
```

### Seed sample data (optional)

Load ~195 pre-written journal entries — useful for testing AI insights without having to write entries manually.

**One-time: create the venv**

```bash
python3 -m venv services/api/.venv
services/api/.venv/bin/pip install -r services/api/requirements.txt
```

**Run the seed script**

```bash
make dev   # stack must be running first

# Use the venv directly (no activation needed)
services/api/.venv/bin/python3 scripts/seed_data/seed_data.py
```

To seed a different user or table:
```bash
USER_ID=alice JOURNAL_TABLE_NAME=journal \
  services/api/.venv/bin/python3 scripts/seed_data/seed_data.py
```

> DynamoDB is in-memory — data is lost when `make dev-down` is run. Re-run the seed script after each restart if needed.

---

### LLM / AI enrichment (optional)

Two AI features are available once a provider is configured:

| Feature | Endpoint |
|---------|----------|
| Per-entry summary + tags | `POST /entries/{id}/ai` |
| Period insights (weekly / monthly / yearly) | `POST /insights/summaries` |

**How overlay files work**

`docker compose up` only reads `docker-compose.yml`. Each LLM provider has its own overlay file merged in with `-f`:

```
docker-compose.yml          ← always required (base stack)
docker-compose.ollama.yml   ← adds Ollama containers + injects env into api
docker-compose.groq.yml     ← injects Groq env into api (no extra containers)
docker-compose.openai.yml   ← injects OpenAI env into api (no extra containers)
```

**Quick reference**

```bash
# No LLM
make dev

# Ollama (local, no API key — downloads ~2 GB model on first run)
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build

# Groq (cloud, free tier — get key at https://console.groq.com)
export GROQ_API_KEY=gsk_...
docker compose -f docker-compose.yml -f docker-compose.groq.yml up --build

# OpenAI
export OPENAI_API_KEY=sk-...
docker compose -f docker-compose.yml -f docker-compose.openai.yml up --build
```

Stop using the same `-f` set:
```bash
make dev-down   # base stack only
docker compose -f docker-compose.yml -f docker-compose.ollama.yml down --remove-orphans
```

### RAG — "Ask Your Journal" (optional)

```bash
docker compose -f docker-compose.yml \
               -f docker-compose.ollama.yml \
               -f docker-compose.rag.yml \
               up --build
```

This adds ChromaDB (vector store) and pulls the `nomic-embed-text` embedding model (~275 MB on first run).

**Usage:** seed entries → open **Ask** tab → click **"Index all entries"** → ask questions.

---

### Run tests

```bash
make test
# Runs 112 tests via pytest with moto-mocked DynamoDB. No Docker required.
```

Or manually:
```bash
source services/api/.venv/bin/activate
pytest services/ -v
```

### Stop / clean up

```bash
make dev-down             # stop containers (data lost — DynamoDB is in-memory)
docker compose up --build # full rebuild after code changes
```

---

## AWS deployment

Terraform modules are in `infra/terraform/`. All deploy steps are available as `make` targets — run `make help` to see the full list.

**AWS stack**

| Layer | AWS service |
|-------|-------------|
| Web   | S3 + CloudFront |
| API   | Lambda (serverless) or App Runner (container) |
| DB    | DynamoDB on-demand |
| Auth  | Cognito (PKCE) |
| AI    | Bedrock (Nova Lite + Titan Embeddings) or Groq via Step Functions + Lambda |

**Compute modes** (set in `dev.tfvars`):

| `compute_mode` | API runtime | Use when |
|----------------|-------------|----------|
| `serverless`   | Lambda + API Gateway | Default — cheapest, no cold-start issues at low traffic |
| `container`    | App Runner (ECR image) | Need container-specific deps, long-lived connections |
| `hybrid`       | Lambda for CRUD, App Runner for AI | Gradual migration |

---

### First-time deploy — step by step

All `make` targets accept `ENV` and `PROFILE` overrides (default: `ENV=dev PROFILE=journal-dev`).

**Step 1 — Configure AWS CLI** (one-time per machine)

```bash
aws configure --profile journal-dev
export AWS_PROFILE=journal-dev
aws sts get-caller-identity   # verify
```

See `scripts/setup/step-1-aws-configure.md` for full instructions.

**Step 2 — Bootstrap Terraform backend** (one-time per account)

Creates the S3 state bucket and DynamoDB lock table.

```bash
make bootstrap
# ENV=dev PROFILE=journal-dev ./scripts/setup/step-2-bootstrap-terraform-backend.sh dev
```

**Step 3 — Configure tfvars**

```bash
cp infra/terraform/environments/dev/dev.tfvars.example \
   infra/terraform/environments/dev/dev.tfvars
# Edit the file — review the ai_enabled, llm_provider, and bedrock_region settings
```

> `cognito_domain_prefix` is auto-generated if left empty. `callback_urls` and `logout_urls` are patched automatically with the CloudFront URL after the first apply.

**Step 4 — Store secrets and user allowlist in SSM**

Edit `.env.users` (copy from `.env.users.example`) and add your users:

```
# .env.users — format: email=admin|user
you@example.com=admin
friend@example.com=user
```

Then push to SSM:

```bash
make secrets
# Stores: cognito/allowed_emails, admin_emails, groq_api_key (if using Groq)
```

**Step 5 — Terraform apply**

```bash
make infra
# Runs terraform init → plan → apply, then writes apps/web/.env
```

**Step 6 — Create admin Cognito user** (post-deploy)

```bash
make cognito-admin
```

**Step 7 — Deploy web app**

```bash
make deploy-web
# Builds React app → syncs to S3 → CloudFront invalidation
```

---

### Iterative backend deploys

Use `make deploy-backend` instead of `make infra` for code-only changes — it's targeted and much faster:

```bash
make deploy-backend     # Lambda API + AI Gateway + Step Functions
make deploy-routes      # same + update API Gateway routes (when api_routes map changed)
make deploy-api         # API Lambda only (fastest)
make deploy-ai          # AI Gateway Lambda only
make deploy-sfn         # Step Functions state machine only
```

Deploy backend + frontend together:
```bash
make deploy             # deploy-backend + deploy-web
make deploy-all-routes  # deploy-routes + deploy-web
```

---

### Managing users and admins

The user allowlist and admin list live in `.env.users` and are pushed to SSM via `make secrets`.

| Action | Steps | Redeploy? |
|--------|-------|-----------|
| Add a **new user** (can sign up) | Edit `.env.users` → `make secrets` | **No** — pre-signup Lambda reads SSM live on each invocation |
| Add/change an **admin** | Edit `.env.users` → `make secrets` → `make deploy-backend` | **Yes** — `ADMIN_EMAILS` is a Lambda env var set at deploy time |

> The pre-signup Lambda reads `cognito/allowed_emails` from SSM on every sign-up attempt (no caching), so user allowlist changes take effect immediately. Admin changes require a Lambda redeploy to update the `ADMIN_EMAILS` environment variable.

---

### AI provider configuration

AI enrichment uses Bedrock by default (Nova Lite for LLM, Titan Embeddings V2 for RAG). Groq is available as an alternative.

**Enable AI in tfvars:**

```hcl
# infra/terraform/environments/dev/dev.tfvars
ai_enabled        = "true"
llm_provider      = "bedrock"       # "bedrock" | "groq"
bedrock_region    = "us-east-1"     # Bedrock model availability — us-east-1 recommended
```

> Bedrock calls always route to `BEDROCK_REGION` (default `us-east-1`) even if your stack is in `ca-central-1`. IAM cross-region calls are allowed — no extra config needed.

**To use Groq instead:**

```hcl
llm_provider = "groq"
```

Store the key:
```bash
LLM_PROVIDER=groq make secrets
```

Then redeploy:
```bash
make deploy-backend
```

The runtime provider can also be overridden **per-request** from the UI using the provider dropdown — this passes `X-LLM-Provider: bedrock|groq` which is forwarded through Step Functions input.

---

### Container / hybrid mode (optional)

```bash
# Build and push Docker image to ECR
make build-container   # or: AWS_PROFILE=journal-dev ./scripts/setup/step-3b-build-push-container.sh dev
```

Then update `dev.tfvars`:
```hcl
compute_mode        = "container"   # or "hybrid"
container_image_uri = "123456789.dkr.ecr.ca-central-1.amazonaws.com/journal-dev-api:latest"
```

Then apply:
```bash
make infra
```

---

### Seed data to AWS DynamoDB

```bash
AWS_PROFILE=journal-dev ./scripts/seed_data/seed-aws.sh dev
```

Or directly:
```bash
DYNAMODB_ENDPOINT="" \
AWS_DEFAULT_REGION=ca-central-1 \
JOURNAL_TABLE_NAME=journal-dev-journal \
  services/api/.venv/bin/python3 scripts/seed_data/seed_data.py
```

---

### Tear down

```bash
# Destroy all Terraform resources
AWS_PROFILE=journal-dev ./scripts/destroy/step-1a-terraform-destroy.sh dev

# Delete ECR repo (container/hybrid mode only)
AWS_PROFILE=journal-dev ./scripts/destroy/step-1b-delete-ecr-repo.sh dev

# Delete Terraform backend (permanent — prompts for confirmation)
./scripts/destroy/step-1c-delete-terraform-backend.sh

# Verify everything is gone
AWS_PROFILE=journal-dev ./scripts/destroy/step-1d-verify-destroy.sh dev
```
