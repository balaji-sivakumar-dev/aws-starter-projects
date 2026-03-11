# Template 3 — Containerised Journal Starter Kit

Full-stack journal app: **Python FastAPI** + **React** + **DynamoDB** — everything runs as Docker containers locally, deployable to AWS (ECS/Fargate or Lambda) via Terraform.

## Quick start

```bash
docker compose up --build
# Web UI  → http://localhost:3000
# API     → http://localhost:8080/docs
```

→ **[Full local setup guide](local-setup.md)**

## Architecture

| Layer | Local | AWS |
|-------|-------|-----|
| Web | Nginx container (port 3000) | S3 + CloudFront |
| API | FastAPI container (port 8080) | ECS/Fargate **or** Lambda |
| DB | `amazon/dynamodb-local` | DynamoDB on-demand |
| Auth | `X-User-Id` header bypass | Cognito PKCE |
| AI | Ollama / Groq / OpenAI (swappable via `LLM_PROVIDER`) | Bedrock / Step Functions |

## API deployment modes

The Python API is structured to support three deployment modes without changing business logic:

| Mode | Entrypoint | When to use |
|------|-----------|-------------|
| Docker container | `src.main:app` (uvicorn) | Local dev, ECS/Fargate |
| Lambda container (Mangum) | `src.lambda_mangum.handler` | Lambda with full FastAPI stack |
| Lambda direct (no framework) | `src.lambda_handler.handler` | Lambda with minimal cold start |

## Docs

- [Local Setup](local-setup.md)
- [Implementation Plan](implementation_plan.md)
- [Architecture](docs/Architecture.md)
- [API Contract](docs/API.md)
- [Execution Plan](docs/ExecutionPlan.md)
