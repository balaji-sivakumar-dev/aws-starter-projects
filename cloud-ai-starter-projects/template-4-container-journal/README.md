# Template 4 — Container Journal (App Runner)

> **Status: Scoped — Not yet built**
> This template is planned but not implemented. See [`docs/Scope.md`](docs/Scope.md) for design decisions, architecture, and build plan.

---

## What is this?

Template 4 is a **pure container deployment** of the Reflect journal app. It builds on the same product as Template 3 (Serverless Lambda), but replaces the Lambda API with a **Node.js/Express API running on AWS App Runner**.

The goal is to demonstrate the same application architecture deployed in two different compute styles, side by side:

| | Template 3 | Template 4 |
|---|---|---|
| API runtime | Python (AWS Lambda) | Node.js (AWS App Runner) |
| Scaling model | Per-request (Lambda cold start) | Always-warm container |
| Deployment unit | ZIP archive | Docker image (ECR) |
| API Gateway | HTTP API (Lambda proxy) | HTTP API (HTTP proxy) |
| AI pipeline | Step Functions + Lambda | Step Functions + Lambda (shared pattern) |
| Auth | Cognito Hosted UI | Cognito Hosted UI |
| Frontend | React SPA (CloudFront + S3) | React SPA (CloudFront + S3) |

---

## Quick reference — planned stack

```
Browser (CloudFront → S3 SPA)
    │
    ▼
API Gateway v2 (HTTP API + JWT authorizer)
    │
    ▼
AWS App Runner ◄── ECR (Docker image)
    │              Node.js / Express
    ├── DynamoDB (on-demand, single-table)
    └── Step Functions ──► AI Gateway Lambda
                              └── Bedrock / Groq
```

---

## Relationship to Template 3

Template 3 already contains a `compute_mode` variable that supports `serverless`, `container`, or `hybrid`. Template 4 **extracts** the container path into its own standalone template so it can:

- Evolve independently without breaking the Lambda template
- Be a clean reference for teams choosing App Runner over Lambda
- Have simplified scripts (no hybrid mode, no Lambda zip management)

---

## Where to start

When implementation begins, follow [`docs/Scope.md`](docs/Scope.md) — it lists every component, the gaps to fill, and the build sequence.
