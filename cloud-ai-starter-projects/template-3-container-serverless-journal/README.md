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

## Deploy

A `Makefile` wraps all deploy scripts. Run `make help` to see all targets.

```bash
# First-time setup
make bootstrap          # create Terraform S3 backend
make secrets            # store API keys + user allowlist in SSM
make infra              # terraform apply (full deploy)
make cognito-admin      # create admin user in Cognito

# Iterative deploys
make deploy-backend     # Lambda API + AI Gateway + Step Functions
make deploy-routes      # same + update API Gateway routes
make deploy-web         # build React app → S3 + CloudFront invalidation
make deploy             # backend + web together

# Local dev
make dev                # docker compose up (full stack)
make test               # run Python tests
make web-dev            # Vite dev server (localhost:5173)
```

## Docs

| Doc | Description |
|-----|-------------|
| [Architecture](docs/Architecture.md) | System design, data model, API contract, deployment modes |
| [Architecture Diagram](docs/Reflect%20APP%20AWS.drawio.xml) | AWS architecture diagram (draw.io) — open with `npx @drawio/mcp` or [app.diagrams.net](https://app.diagrams.net) |
| [Setup](docs/Setup.md) | Local dev, seed data, LLM config, running tests, AWS deployment scripts |
| [Testing-Local](docs/Testing-Local.md) | Step-by-step guide to run and test the full stack locally, including RAG |
| [AWS-Console-Setup](docs/AWS-Console-Setup.md) | Manual AWS console steps after Terraform deploy (allowlist, admin user, TTL, alarms) |
| [AWS-Cost-Estimate](docs/AWS-Cost-Estimate.md) | Monthly cost breakdown by compute mode; what to keep running vs shut down after testing |
| [Checklist](IMPLEMENTATION_CHECKLIST.md) | Implementation progress (requirements, issues, fixes) |

## Tooling

### draw.io MCP (architecture diagrams)

The AWS architecture diagram (`docs/Reflect APP AWS.drawio.xml`) can be viewed and edited using the draw.io MCP server, which lets Claude open and update diagrams directly.

```bash
# Add to your Claude Code MCP configuration:
npx @drawio/mcp

# Or run via Makefile:
make drawio
```

Add it to `.claude/settings.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "drawio": {
      "command": "npx",
      "args": ["@drawio/mcp"]
    }
  }
}
```
