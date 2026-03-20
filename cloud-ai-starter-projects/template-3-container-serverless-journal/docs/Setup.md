# Setup Guide — Template 3

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

docker compose up --build
```

Three containers start in dependency order:

| Container | Role | Port |
|-----------|------|------|
| `t3-dynamodb` | DynamoDB Local (in-memory) | 8000 |
| `t3-api` | Python FastAPI | 8080 |
| `t3-web` | React + Nginx | 3000 |

The API auto-creates the `journal` table on startup. The UI runs in **local mode** — no login required (all requests use `dev-user`).

Open:
- Web UI → http://localhost:3000
- API docs → http://localhost:8080/docs

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

Load 20 pre-written journal entries (Oct 2025 – Mar 2026, covering work, family, and travel) — useful for testing AI insights without having to write entries manually.

**All commands run from the template-3 root directory** (same folder as `docker-compose.yml`).

**One-time: create the venv and install dependencies**

```bash
# Create the venv inside services/api/ (only needed once)
python3 -m venv services/api/.venv

# Install dependencies
services/api/.venv/bin/pip install -r services/api/requirements.txt
```

**Run the seed script**

```bash
# Stack must be running first
docker compose up -d

# Option A — use the venv directly (no activation needed)
services/api/.venv/bin/python3 scripts/seed_data/seed_data.py

# Option B — activate the venv first, then use plain python3
source services/api/.venv/bin/activate
python3 scripts/seed_data/seed_data.py
deactivate   # when done
```

To seed a different user or table:
```bash
USER_ID=alice JOURNAL_TABLE_NAME=journal \
  services/api/.venv/bin/python3 scripts/seed_data/seed_data.py
```

To seed into AWS DynamoDB instead of local:
```bash
DYNAMODB_ENDPOINT="" AWS_DEFAULT_REGION=us-east-1 \
  services/api/.venv/bin/python3 scripts/seed_data/seed_data.py
```

> DynamoDB is in-memory — data is lost when `docker compose down` is run. Re-run the seed script after each restart if needed.

---

### LLM / AI enrichment (optional)

Two AI features are available once a provider is configured:

| Feature | Endpoint |
|---------|----------|
| Per-entry summary + tags | `POST /entries/{id}/ai` |
| Period insights (weekly / monthly / yearly) | `POST /insights/summaries` |

**How overlay files work**

`docker compose up` only reads `docker-compose.yml`. Each LLM provider has its own overlay file that is merged in with `-f`. Passing two `-f` flags merges the files — the overlay adds or overrides only what it declares, leaving everything else unchanged.

```
docker-compose.yml          ← always required (base stack)
docker-compose.ollama.yml   ← adds Ollama containers + injects env into api
docker-compose.groq.yml     ← injects Groq env into api (no extra containers)
docker-compose.openai.yml   ← injects OpenAI env into api (no extra containers)
```

**Quick reference**

```bash
# No LLM
docker compose up --build

# Ollama (local, no API key needed — downloads ~2 GB model on first run)
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build

# Groq (cloud, free tier — get key at https://console.groq.com)
export GROQ_API_KEY=gsk_...
docker compose -f docker-compose.yml -f docker-compose.groq.yml up --build

# OpenAI
export OPENAI_API_KEY=sk-...
docker compose -f docker-compose.yml -f docker-compose.openai.yml up --build
```

Stop commands must use the same `-f` set used to start, so Compose knows which containers belong to the stack:

```bash
# Stop base stack
docker compose down --remove-orphans

# Stop base + Ollama
docker compose -f docker-compose.yml -f docker-compose.ollama.yml down --remove-orphans
```

> Always use `--remove-orphans` with `down` to avoid stale containers causing name conflicts on the next start.

**Ollama details**

The Ollama overlay adds two extra containers:
- `t3-ollama` — Ollama server (port 11434, reachable from host too: `ollama run llama3.2`)
- `t3-ollama-pull` — one-shot container that pulls `llama3.2` into a persistent volume on first run

To switch models, set `OLLAMA_MODEL` before starting:
```bash
OLLAMA_MODEL=llama3.1 docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build
```

**`ollama run` (host install) vs the Docker overlay**

If you already have the [Ollama app](https://ollama.com) installed on your Mac, you have two options:

| | Docker overlay (`docker-compose.ollama.yml`) | Host Ollama (`ollama run`) |
|---|---|---|
| **Requires** | Docker only — nothing else installed | Ollama app installed on your Mac |
| **Where it runs** | Ollama server inside a Docker container | Ollama server on your Mac directly |
| **Model storage** | `ollama-data` Docker named volume | `~/.ollama` on your Mac |
| **Network path** | Container → container (`http://ollama:11434`) | Container → host (`http://host.docker.internal:11434`) |
| **First-run download** | Automatic via `ollama-pull` one-shot container | You run `ollama pull llama3.2` yourself |
| **Best for** | Teams / reproducible setup (zero host install) | You already have Ollama + models downloaded |

To use your **host Ollama** instead of the overlay (skips the ~2 GB download if you already have the model):

```bash
# 1. Make sure Ollama is running on your Mac (open the app, or: ollama serve)
# 2. Pull the model if you haven't already
ollama pull llama3.2

# 3. Start the base stack only, pointing the API at your host Ollama
LLM_PROVIDER=ollama OLLAMA_HOST=http://host.docker.internal:11434 \
  docker compose up --build
```

`host.docker.internal` is a special DNS name Docker provides so containers can reach services running on the host machine.

**Groq / OpenAI details**

These overlays only inject environment variables — no extra containers are added. API keys are read from your shell environment and never written into the compose files.

```bash
# Override the default model
GROQ_MODEL=llama-3.1-8b-instant docker compose -f docker-compose.yml -f docker-compose.groq.yml up --build
OPENAI_MODEL=gpt-4o              docker compose -f docker-compose.yml -f docker-compose.openai.yml up --build
```

OpenAI-compatible endpoints (Azure, Together AI, vLLM, etc.) can be used by also setting `OPENAI_BASE_URL`:
```bash
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://api.together.xyz/v1
docker compose -f docker-compose.yml -f docker-compose.openai.yml up --build
```

### RAG — "Ask Your Journal" (optional)

RAG adds semantic search + AI-powered Q&A over your journal entries. It requires an LLM provider (Ollama recommended for local) plus the RAG overlay.

**Start with RAG support**

```bash
# Ollama for both LLM + embeddings, plus ChromaDB for vector storage
docker compose -f docker-compose.yml \
               -f docker-compose.ollama.yml \
               -f docker-compose.rag.yml \
               up --build
```

This adds two extra containers:

| Container | Role | Port |
|-----------|------|------|
| `t3-chromadb` | ChromaDB vector store | 8001 |
| `t3-ollama-pull-embed` | One-shot: pulls `nomic-embed-text` embedding model | — |

First startup downloads the embedding model (~275 MB) in addition to the LLM model.

**Usage**

1. Seed or create some journal entries
2. Open http://localhost:3000 → click the **Ask** tab
3. Click **"Index all entries"** to embed your entries into ChromaDB
4. Ask questions like "What was I stressed about recently?" or "Find entries about family"

Two modes are available:
- **Conversational** — AI reads matching entries and generates a natural-language answer with source citations
- **Search only** — returns matching entries ranked by semantic similarity (no LLM call)

**Stop with RAG**

```bash
docker compose -f docker-compose.yml \
               -f docker-compose.ollama.yml \
               -f docker-compose.rag.yml \
               down --remove-orphans
```

---

### Inspect DynamoDB

```bash
# AWS CLI
aws dynamodb scan --table-name journal \
  --endpoint-url http://localhost:8000 \
  --region us-east-1 \
  --no-sign-request

# GUI: NoSQL Workbench → Add connection → localhost:8000
```

### Stop / clean up

```bash
# Stop and remove all containers (data lost — DynamoDB is in-memory)
docker compose down --remove-orphans

# Full rebuild after code changes
docker compose up --build
```

---

## Run tests

Tests use `moto` to mock DynamoDB — no Docker required.

```bash
cd services/api
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/pytest tests/ -v
# 56 tests, ~3 s
```

## Activate venv
```bash
cd cloud-ai-starter-projects/template-3-container-serverless-journal
python3 -m venv venv
source venv/bin/activate
```


---

## AWS deployment

Terraform modules are in `infra/terraform/`. Setup and destroy scripts are in `scripts/`.

**AWS stack**

| Layer | AWS service |
|-------|-------------|
| Web   | S3 + optional CloudFront |
| API   | AWS Lambda **or** App Runner (Docker) — controlled by `compute_mode` |
| DB    | DynamoDB on-demand |
| Auth  | Cognito (PKCE) |
| AI    | Groq or Bedrock via Step Functions + Lambda (disabled by default) |

**Compute modes** (set in `dev.tfvars`):

| `compute_mode` | API runtime | Use when |
|----------------|-------------|----------|
| `serverless`   | Lambda + API Gateway | Default — cheapest, no cold-start issues at low traffic |
| `container`    | App Runner (ECR image) | Need container-specific deps, long-lived connections |
| `hybrid`       | Lambda for CRUD, App Runner for AI | Gradual migration / A/B |

---

### Setup — step by step

All scripts run from the **repo root**. Set `AWS_PROFILE=journal-dev` in your shell first (see step 1).

**Step 1 — Configure AWS CLI** (one-time per machine)

```bash
# Follow the instructions in:
cat scripts/setup/step-1-aws-configure.md
```

```bash
aws configure --profile journal-dev
export AWS_PROFILE=journal-dev
aws sts get-caller-identity   # verify
```

**Step 2 — Bootstrap Terraform backend** (one-time per account)

Creates the S3 state bucket and DynamoDB lock table, then writes `infra/terraform/backend.dev.tfbackend`.

```bash
./scripts/setup/step-2-bootstrap-terraform-backend.sh dev
```

Optional overrides:
```bash
REGION=eu-west-1 PROJECT_PREFIX=myapp ./scripts/setup/step-2-bootstrap-terraform-backend.sh dev
```

**Step 3 — Configure tfvars**

```bash
cp infra/terraform/environments/dev/dev.tfvars.example \
   infra/terraform/environments/dev/dev.tfvars
# Edit the file — at minimum review the AI section below
```

> `cognito_domain_prefix` is auto-generated by step 3A if left empty. `callback_urls` and `logout_urls` are patched automatically with the CloudFront URL.

**Step 3A — Terraform apply** (serverless mode — no container needed)

```bash
./scripts/setup/step-3a-terraform-apply.sh dev
```

Runs `terraform init → plan → apply`, then writes `apps/web/.env` with the API URL and Cognito config.

**Step 2B — Store secrets in SSM** (required for AI features)

The Groq API key is stored in AWS SSM Parameter Store — never in tfvars or code.

```bash
./scripts/setup/step-2b-store-secrets.sh dev
# Prompts for your Groq API key and stores it at /journal/dev/groq_api_key (SecureString)
# Get a free key at: https://console.groq.com
```

**Step 3A (optional) — Enable AI enrichment**

AI is **disabled by default**. To enable it, edit `dev.tfvars` and re-run step 3A:

```hcl
# infra/terraform/environments/dev/dev.tfvars
ai_enabled    = "true"
llm_provider  = "groq"                   # "groq" | "bedrock"
groq_model_id = "llama-3.1-8b-instant"  # or llama-3.3-70b-versatile for higher quality
```

> Do **not** put the API key in tfvars — run `step-2b-store-secrets.sh` instead. Terraform reads it from SSM at apply time.

Then apply:

```bash
./scripts/setup/step-3a-terraform-apply.sh dev
```

This deploys the AI Gateway Lambda and Step Functions state machine. No container rebuild needed — the AI Lambda is a ZIP package.

Two AI features are unlocked once enabled:

| Feature | How to trigger |
|---------|----------------|
| Per-entry summary + tags | Click "AI Enrich" on any journal entry |
| Period insights (weekly / monthly / yearly) | Open Insights panel → Generate Summary |

**Available Groq models** (free tier):

| Model | Speed | Quality |
|-------|-------|---------|
| `llama-3.1-8b-instant` | Fast | Good — default |
| `llama-3.3-70b-versatile` | Slower | Better for longer entries |

---

**Step 3B — Build + push Docker image** (container / hybrid mode only)

```bash
./scripts/setup/step-3b-build-push-container.sh dev
# Prints the full ECR image URI at the end
```

Then update `dev.tfvars`:
```hcl
compute_mode        = "container"   # or "hybrid"
container_image_uri = "123456789.dkr.ecr.us-east-1.amazonaws.com/journal-dev-api:latest"
```

Then re-run step 3A:
```bash
./scripts/setup/step-3a-terraform-apply.sh dev
```

**Step 3C — Deploy backend changes only** (iterative development)

Use this instead of a full `step-3a` apply when you only change Lambda code, IAM, or the Step Functions state machine:

```bash
./scripts/setup/step-3c-deploy-backend.sh dev

# Deploy only a subset:
DEPLOY_SFN=false ./scripts/setup/step-3c-deploy-backend.sh dev   # skip Step Functions
DEPLOY_AI=false  ./scripts/setup/step-3c-deploy-backend.sh dev   # skip AI Gateway Lambda
DEPLOY_API=false ./scripts/setup/step-3c-deploy-backend.sh dev   # skip API Lambda
```

This clears the Lambda ZIP cache, then runs targeted `terraform apply` on only the selected components (does not touch Cognito, DynamoDB, API Gateway, CloudFront, or S3).

**Step 4 — Deploy web app to S3**

```bash
./scripts/setup/step-4a-deploy-web-to-s3.sh dev
```

Reads Terraform outputs, writes `apps/web/.env`, runs `npm build`, syncs to S3, and invalidates CloudFront.

---

### Tear down — step by step

**Step 1A — Destroy Terraform resources**

```bash
./scripts/destroy/step-1a-terraform-destroy.sh dev
```

Destroys all Terraform-managed resources (Lambda, App Runner, DynamoDB, Cognito, S3 web bucket, API Gateway, IAM roles).

**Step 1B — Delete ECR repository** (container / hybrid mode only)

The ECR repo is managed outside Terraform. Delete it separately:

```bash
./scripts/destroy/step-1b-delete-ecr-repo.sh dev
```

**Step 1C — Delete Terraform backend** (optional — permanent state loss)

```bash
./scripts/destroy/step-1c-delete-terraform-backend.sh
```

Deletes the S3 state bucket and DynamoDB lock table. Requires typing `DELETE` to confirm.

**Step 1D — Verify everything is gone**

```bash
./scripts/destroy/step-1d-verify-destroy.sh dev
```

Checks: S3 buckets, DynamoDB tables, Cognito pool, Lambda functions, App Runner service, ECR repo, CloudFront.

---

### Seed data to AWS DynamoDB

After deployment, use the dedicated AWS seed script (handles profile + table name automatically):

```bash
AWS_PROFILE=journal-dev ./scripts/seed_data/seed-aws.sh dev
```

Or run the seed script directly with explicit overrides:

```bash
# Install boto3 if needed
pip install boto3

DYNAMODB_ENDPOINT="" \
AWS_DEFAULT_REGION=ca-central-1 \
JOURNAL_TABLE_NAME=journal-dev-journal \
  python3 scripts/seed_data/seed_data.py
```


```bash
AWS_PROFILE=journal-dev ./scripts/setup/step-2-bootstrap-terraform-backend.sh dev

AWS_PROFILE=journal-dev ./scripts/setup/step-2b-store-secrets.sh dev

AWS_PROFILE=journal-dev ./scripts/setup/step-3a-terraform-apply.sh dev
```


```bash


docker compose -f docker-compose.yml -f docker-compose.ollama.yml -f docker-compose.rag.yml down
docker compose -f docker-compose.yml -f docker-compose.ollama.yml -f docker-compose.rag.yml up --build
services/api/.venv/bin/python3 scripts/seed_data/seed_data.py

SKIP_DOWN=1 VERBOSE=1 bash scripts/tests/test_local_integration.sh
```



