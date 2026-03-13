# Template 3 — Containerised Journal

Full-stack journal app with AI enrichment: **Python FastAPI** + **React** + **DynamoDB** — runs entirely as Docker containers locally, deployable to AWS (ECS/Fargate or Lambda).

## Quick start

```bash
docker compose up --build
# Web UI  → http://localhost:3000
# API     → http://localhost:8080/docs
```

No login required locally — all requests run as `dev-user`.

## Docs

| Doc | Description |
|-----|-------------|
| [Architecture](docs/Architecture.md) | System design, data model, API contract, deployment modes |
| [Setup](docs/Setup.md) | Local dev, running tests, AWS deployment guide |
| [Checklist](docs/Checklist.md) | Implementation progress and planned work |
