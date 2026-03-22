# {{APP_TITLE}}

> Generated from the AWS Full-Stack Starter Template.

## Quick Start (Local)

```bash
make dev          # Start DynamoDB + API + Web via Docker Compose
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
├── routes.yaml                # Single source of truth for API routes
├── template.json              # Template metadata + feature flags
├── docker-compose.yml
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

## Documentation

| Doc | Purpose |
|-----|---------|
| [Usage Guide](docs/Usage-Guide.md) | Create, run, stop, delete projects — full walkthrough |
| [Setup.md](docs/Setup.md) | Step-by-step local + AWS setup |
| [Architecture.md](docs/Architecture.md) | Architecture overview + diagrams |
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
