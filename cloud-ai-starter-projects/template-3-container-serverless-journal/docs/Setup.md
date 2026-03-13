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

Requires the venv created in the [Run tests](#run-tests) section, or any Python environment with `boto3` installed.

```bash
# Stack must be running first
docker compose up -d

# Run the seed script (targets http://localhost:8000 by default)
services/api/.venv/bin/python3 scripts/seed_data.py
```

To seed a different user or table:
```bash
USER_ID=alice JOURNAL_TABLE_NAME=journal services/api/.venv/bin/python3 scripts/seed_data.py
```

To seed into AWS DynamoDB instead of local:
```bash
DYNAMODB_ENDPOINT="" AWS_DEFAULT_REGION=us-east-1 \
  services/api/.venv/bin/python3 scripts/seed_data.py
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

---

## AWS deployment (Phase 4 — planned)

The same API image deploys to ECS/Fargate or Lambda without changing business logic. Terraform modules are in `infra/terraform/`.

Target stack:

| Layer | AWS service |
|-------|-------------|
| Web   | S3 + CloudFront |
| API   | ECS/Fargate (Docker) **or** Lambda (Mangum or direct handler) |
| DB    | DynamoDB on-demand |
| Auth  | Cognito PKCE — set `APP_ENV=production` and `COGNITO_ISSUER` |

Steps (when ready):
1. `aws configure --profile template3-dev`
2. Configure `infra/terraform/environments/dev/dev.tfvars`
3. `terraform init && terraform apply -var-file=environments/dev/dev.tfvars`
4. Build and push API image to ECR
5. Set `VITE_AUTH_MODE=cognito` + Cognito env vars, rebuild the web image
