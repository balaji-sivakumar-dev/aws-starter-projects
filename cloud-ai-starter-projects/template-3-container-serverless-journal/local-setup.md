# Local Setup Guide — Template 3

Everything runs as Docker containers. No local Python or Node installation needed beyond Docker.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | 4.x+ | https://docs.docker.com/get-docker/ |
| Docker Compose | v2 (bundled with Desktop) | — |

> **Optional** for LLM testing: [Ollama](https://ollama.com/download) (if you want local model inference)

---

## 1. Clone and navigate

```bash
git clone https://github.com/balaji-sivakumar-dev/aws-starter-projects.git
cd aws-starter-projects/cloud-ai-starter-projects/template-3-container-serverless-journal
```

---

## 2. Start all services

```bash
docker compose up --build
```

This starts three containers in dependency order:

| Container | Role | Port |
|-----------|------|------|
| `t3-dynamodb` | Amazon DynamoDB Local | 8000 (internal + exposed) |
| `t3-api` | Python FastAPI | 8080 |
| `t3-web` | React + Nginx | **3000** |

The API auto-creates the `journal` DynamoDB table on first startup.

---

## 3. Open the app

- **Web UI** → http://localhost:3000
- **API Swagger** → http://localhost:8080/docs
- **API health** → http://localhost:8080/health

The UI runs in **local mode** — no login required. Requests are sent as `dev-user`.

---

## 4. Call the API directly (optional)

All endpoints accept `X-User-Id: <any-value>` in local mode (no JWT needed).

```bash
# Health
curl http://localhost:8080/health

# Create an entry
curl -s -X POST http://localhost:8080/entries \
  -H "Content-Type: application/json" \
  -H "X-User-Id: dev-user" \
  -d '{"title": "First entry", "body": "Hello journal!"}' | jq

# List entries
curl -s http://localhost:8080/entries \
  -H "X-User-Id: dev-user" | jq
```

---

## 5. LLM / AI enrichment (optional)

Trigger AI summary + tag generation on any entry via `POST /entries/{id}/ai`.

### Option A — Ollama (local, free)

```bash
# 1. Install Ollama: https://ollama.com/download
# 2. Pull a model
ollama pull llama3.2

# 3. Add to docker-compose.yml (or set env vars and restart):
#    api:
#      environment:
#        LLM_PROVIDER: ollama
#        OLLAMA_HOST: http://host.docker.internal:11434
#        OLLAMA_MODEL: llama3.2
```

### Option B — Groq (cloud, free tier)

```bash
# 1. Sign up at https://console.groq.com → create an API key
# 2. Set env vars in docker-compose.yml under the api service:
#    LLM_PROVIDER: groq
#    GROQ_API_KEY: gsk_...
#    GROQ_MODEL: llama-3.3-70b-versatile
```

### Option C — OpenAI

```bash
# 1. Get API key from https://platform.openai.com
# 2. Set env vars:
#    LLM_PROVIDER: openai
#    OPENAI_API_KEY: sk-...
#    OPENAI_MODEL: gpt-4o-mini
```

After setting the provider, trigger AI on an entry:

```bash
curl -s -X POST http://localhost:8080/entries/<entry-id>/ai \
  -H "X-User-Id: dev-user" | jq
```

The response will include `summary` and `tags` written back to DynamoDB.

---

## 6. Inspect DynamoDB locally

Use [NoSQL Workbench](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/workbench.settingup.html) (free GUI):

1. Open NoSQL Workbench → **Operation builder**
2. Add connection: `localhost:8000` (no credentials needed)
3. Browse the `journal` table

Or use AWS CLI:

```bash
aws dynamodb scan --table-name journal \
  --endpoint-url http://localhost:8000 \
  --region us-east-1 \
  --no-sign-request
```

---

## 7. Rebuild after code changes

```bash
# Rebuild and restart a single service
docker compose up --build api

# Full rebuild
docker compose up --build
```

---

## 8. Stop and clean up

```bash
# Stop containers (keeps DynamoDB data volume)
docker compose down

# Stop and wipe all data (DynamoDB volume deleted)
docker compose down -v
```

---

## Deployment modes (for reference)

| Mode | Entrypoint | Command |
|------|-----------|---------|
| Docker container | `src.main:app` | `uvicorn src.main:app` (Dockerfile default) |
| Lambda container (Mangum) | `src.lambda_mangum.handler` | Set Lambda handler in Terraform |
| Lambda direct (zip) | `src.lambda_handler.handler` | Set Lambda handler in Terraform |

See [Architecture.md](docs/Architecture.md) for the full deployment picture.
