# AWS Full-Stack Starter Template

> **This is the base template.** Use `make new-project` to scaffold a new app from it (see below).
> The generated project will use your app name in place of all `{{APP_TITLE}}` placeholders.

---

## Creating a New App

Run from `aws-starter-projects/` (the repo root — one level above `cloud-ai-starter-projects/`):

```bash
cd aws-starter-projects

# Interactive — prompts for app name, AWS region, and features to enable
make new-project APP=myapp

# Skip all prompts, use defaults
make new-project APP=myapp DEFAULTS=true

# Output to a custom path outside this repo (standalone project)
make new-project APP=myapp OUT=~/projects/myapp
```

The generated project lands in `generated/myapp/` (gitignored) or your custom `OUT` path.
`cd` into it and follow the Quick Start below.

---

## Quick Start (Local)

```bash
make dev          # Full stack: DynamoDB + API + Web + Ollama AI + ChromaDB RAG
make dev-minimal  # CRUD only (no AI/RAG, fastest startup)
# Web UI  → http://localhost:3000
# API     → http://localhost:8080/docs
```

## Quick Start (AWS Deploy)

```bash
make bootstrap    # Create Terraform S3 backend + lock table
make secrets      # Store API keys + user allowlist in SSM
make infra        # Terraform init + plan + apply
make deploy       # Deploy Lambda API + web to S3/CloudFront
make cognito-admin # Create admin user in Cognito
```

## Architecture

| Layer | Technology |
|-------|-----------|
| Frontend | React (Vite) + Nginx |
| API | Python FastAPI → Lambda + API Gateway v2 |
| Database | DynamoDB (single-table, PK/SK) |
| Auth | Cognito User Pool (PKCE + id_token JWT) |
| Hosting | S3 + CloudFront (OAC) |
| AI (opt-in) | Step Functions + Lambda AI Gateway (Bedrock / Groq) |
| RAG (opt-in) | Bedrock Titan Embeddings V2 + DynamoDB vector store |
| IaC | Terraform (modular) |

## Project Structure

```
├── apps/web/                  # React SPA
├── services/
│   ├── api/                   # FastAPI + business logic + tests
│   ├── lambda_api/            # Lambda handler wrapper
│   └── workflows/             # [opt-in] AI Gateway
├── infra/terraform/           # Terraform modules
├── scripts/
│   ├── config.sh              # Shared deployment constants
│   ├── setup/                 # Numbered deploy scripts
│   └── destroy/               # Teardown scripts
├── docker/
│   ├── docker-compose.yml     # Main local dev stack
│   ├── docker-compose.groq.yml
│   ├── docker-compose.ollama.yml
│   └── ...                    # Provider-specific overrides
├── routes.yaml                # Single source of truth for API routes
├── template.json              # Template metadata + feature flags
├── Makefile
└── CLAUDE.md                  # AI assistant rules
```

## Make Targets

| Target | What it does |
|--------|-------------|
| `make dev` | Start local stack (Docker Compose) |
| `make dev-down` | Stop local stack |
| `make test` | Run Python tests |
| `make bootstrap` | Create Terraform backend (S3 + DynamoDB lock) |
| `make secrets` | Store SSM parameters (API keys, user emails) |
| `make infra` | Full Terraform apply |
| `make deploy` | Deploy backend + frontend |
| `make deploy-backend` | Lambda + AI Gateway + Step Functions |
| `make deploy-web` | Build React + sync S3 + invalidate CloudFront |
| `make validate-routes` | Check routes.yaml vs Terraform + handler |
| `make cognito-admin` | Create admin Cognito user |
| `make docker-clean` | Stop all containers + prune unused images/cache |

> **Note:** All `make` commands must be run from the `_base-template/` directory (or the project root after `make new-project`).

## Documentation

| Doc | Purpose |
|-----|---------|
| [Setup Guide](docs/Setup.md) | Local dev setup + AWS deployment walkthrough |
| [Architecture](docs/Architecture.md) | Architecture overview + diagrams |
| [routes.yaml](routes.yaml) | API endpoint definitions |
| [CLAUDE.md](CLAUDE.md) | AI assistant rules for this project |

## Features

All features are opt-in via `template.json`:

| Feature | Description | Default |
|---------|------------|---------|
| AI Enrichment | Auto-summarize + tag items via Bedrock/Groq | On |
| RAG / Ask | Chat with your data using embeddings | On |
| Admin Dashboard | Audit log + user metrics | On |
| CSV Import | Bulk import with preview | On |
| Period Insights | Weekly/monthly AI summaries | On |
