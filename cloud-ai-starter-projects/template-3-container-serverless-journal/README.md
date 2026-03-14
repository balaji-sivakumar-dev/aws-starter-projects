# Reflect — AI-Powered Journal

**Reflect** is a full-stack journal app with AI-powered enrichment and insights. Built with **Python FastAPI + React + DynamoDB**, it runs locally via Docker and deploys to AWS (Lambda serverless or App Runner container).

## Purpose

This project serves two goals:

1. **Deployable app** — a working, testable application on AWS that demonstrates the full architecture end-to-end (auth, API, database, AI enrichment, period insights).

2. **Production template** — a reusable starting point for building production-grade applications on the same stack. Clone it, rename it, and extend it without starting from scratch.

## Architecture at a glance

| Layer | Local | AWS |
|-------|-------|-----|
| Frontend | React + Nginx (Docker) | S3 + CloudFront |
| API | FastAPI (Docker) | Lambda (`serverless`) or App Runner (`container`) |
| Database | DynamoDB Local (in-memory) | DynamoDB on-demand |
| Auth | Header bypass (`dev-user`) | Cognito PKCE |
| AI (per-entry) | Ollama / Groq / OpenAI | AWS Bedrock (Step Functions) |
| AI (insights) | Ollama / Groq / OpenAI | Ollama / Groq / OpenAI |

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
| [Setup](docs/Setup.md) | Local dev, seed data, LLM config, running tests, AWS deployment scripts |
| [Checklist](docs/Checklist.md) | Implementation progress |
