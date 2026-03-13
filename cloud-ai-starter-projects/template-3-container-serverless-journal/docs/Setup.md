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

### LLM / AI enrichment (optional)

Trigger AI summary + tag generation: `POST /entries/{id}/ai`

**Ollama (local, fully containerised — recommended for first test)**

Use the provided overlay file. Downloads `llama3.2` (~2 GB) on first run; subsequent starts use the cached volume.

```bash
docker compose -f docker-compose.yml -f docker-compose.llm.yml up --build
```

The overlay adds:
- `t3-ollama` — Ollama server (port 11434)
- `t3-ollama-pull` — one-shot container that pulls `llama3.2`
- `LLM_PROVIDER=ollama` wired into the api service automatically

**Groq (cloud, free tier)**

Set env vars in `docker-compose.yml` under the `api` service, then `docker compose up --build api`.

```yaml
LLM_PROVIDER: groq
GROQ_API_KEY: gsk_...         # get from https://console.groq.com
GROQ_MODEL: llama-3.3-70b-versatile
```

**OpenAI**
```yaml
LLM_PROVIDER: openai
OPENAI_API_KEY: sk-...
OPENAI_MODEL: gpt-4o-mini
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
docker compose down       # stop containers (data lost — DynamoDB is in-memory)
docker compose up --build # full rebuild after code changes
```

---

## Run tests

Tests use `moto` to mock DynamoDB — no Docker required.

```bash
cd services/api
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/pytest tests/ -v
# 28 tests, ~1.6 s
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
