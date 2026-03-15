# Template 4 — Reusable Full-Stack Platform Template

> **Status: Design phase — Not yet built**
> See [`docs/`](docs/) for architecture analysis, scope, and recommendations.

---

## What is this?

Template 4 is a **reusable application platform** — a production-grade starter template designed to bootstrap multiple full-stack apps that share common infrastructure needs but differ in business logic.

It builds on the lessons learned from Template 3 (Reflect Journal App) and generalizes the architecture to support a family of applications:

| App | Domain | Key capabilities needed |
|-----|--------|------------------------|
| **Personal Budget Tracker** | FinTech | Document parsing (CSV/Excel/PDF), categorization, analytics |
| **Tax Processor** | FinTech/Legal | Document OCR, data extraction, external API integration |
| **Curriculum Platform** | EdTech | Content management, exam generation, performance analytics |
| **Family Tree** | Social/Personal | Graph relationships, media uploads, sharing/collaboration |

---

## Why a reusable template?

All four apps share the same core needs:

- Scalable, secure UI (React SPA + CloudFront)
- Scalable backend API (Lambda or Container)
- Authentication and authorization (Cognito)
- Structured data storage (DynamoDB)
- Optional LLM/AI integration (Bedrock, Groq, OpenAI)
- Optional RAG-based memory (embeddings + vector search)
- File/document upload and processing (S3 + processing pipeline)
- Local-first development (Docker Compose → AWS)
- Cost optimization (pay-per-use until customer base grows)
- AI vendor portability (swap providers without code changes)

Building each from scratch is wasteful. This template provides the **shared 80%** so each app only needs to build the **unique 20%**.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [`docs/Scope.md`](docs/Scope.md) | Project scope, target apps, shared vs app-specific layers |
| [`docs/Architecture-Analysis.md`](docs/Architecture-Analysis.md) | Deep analysis of Template 3, what to keep/change/add for the platform |
| [`docs/RAG-Design.md`](docs/RAG-Design.md) | RAG pipeline design — embeddings, vector store, retrieval, and query flow |
| [`docs/Scaling-Strategy.md`](docs/Scaling-Strategy.md) | Lambda vs Container vs Microservices — when to use each, evolution path, code organization |
| [`docs/Bootstrap-Template.md`](docs/Bootstrap-Template.md) | GitHub Template Repo design — feature tags, bootstrap script, directory structure |
| [`docs/CICD-Strategy.md`](docs/CICD-Strategy.md) | CI/CD evolution — shell scripts → GitHub Actions, monorepo vs split, OIDC credentials |

---

## Relationship to Template 3

Template 3 (Reflect Journal) is a **working proof-of-concept** that validated the core patterns:

- Core + Adapters architecture (business logic separated from framework)
- LLM provider abstraction (swap Ollama/Groq/Bedrock without code changes)
- Single-table DynamoDB design
- Async AI via Step Functions
- Dual-mode auth (local header bypass / Cognito PKCE)
- Docker Compose local dev → AWS deployment

Template 4 **extracts, generalizes, and extends** these patterns into a reusable platform. Template 3 remains as-is — a complete, working reference app.
