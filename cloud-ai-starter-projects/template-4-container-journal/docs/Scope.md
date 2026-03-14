# Template 4 — Container Journal: Scope & Design

> **Status: Scoped — Not yet built**
> Last updated: 2026-03-14

---

## 1. Goal

Build the Reflect journal app as a **pure container deployment** using AWS App Runner as the API compute layer. The product features (journal CRUD, AI enrichment, insights summaries) are identical to Template 3. The infrastructure and runtime are different.

This serves as a reference template for teams who prefer always-warm containers over Lambda cold-start serverless.

---

## 2. What already exists (reuse from Template 3)

Template 3's codebase was designed with this in mind. The following are already built and just need to be wired together:

| Component | Location (Template 3) | Reuse plan |
|-----------|----------------------|------------|
| Node.js/Express API | `services/container_api/src/server.js` | Copy + extend (add Insights endpoints) |
| App Runner Terraform module | `modules/compute_container/` | Copy + fix (add instance IAM role) |
| API Gateway HTTP_PROXY integration | `modules/api_edge/main.tf` | Copy as-is |
| Auth (Cognito) Terraform module | `modules/auth/` | Copy as-is |
| DynamoDB Terraform module | `modules/db/` | Copy as-is |
| AI Gateway Lambda | `modules/ai_gateway/` | Copy as-is |
| Step Functions workflow | `modules/workflow/` | Copy as-is |
| CloudFront + S3 hosting | `modules/web_hosting/` | Copy as-is |
| React frontend | `apps/web/` | Copy as-is |
| Setup/destroy scripts | `scripts/` | Copy + simplify |

---

## 3. Gaps to fill (what needs to be built or fixed)

### Gap 1 — App Runner instance IAM role *(blocker)*

The existing `compute_container/main.tf` creates an ECR pull role (so App Runner can pull the Docker image from ECR) but **no instance role** (so the running container can call AWS APIs).

The Node.js app needs to call DynamoDB and Step Functions. Without an instance IAM role, all AWS SDK calls will fail with AccessDenied.

**What to add to `modules/compute_container/main.tf`:**
- `aws_iam_role` for App Runner instance (`tasks.apprunner.amazonaws.com`)
- Inline policy with:
  - `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:UpdateItem`, `dynamodb:DeleteItem`, `dynamodb:Query` on the journal table and its GSIs
  - `states:StartExecution` on the Step Functions state machine ARN
- Wire the role into `aws_apprunner_service` via `instance_configuration.instance_role_arn`

### Gap 2 — Insights endpoints missing from Node.js API *(feature gap)*

`services/container_api/src/server.js` implements all journal entry endpoints but is missing the full Insights (period summary) feature:

| Endpoint | Status |
|----------|--------|
| `GET /insights/summaries` | ❌ missing |
| `POST /insights/summaries` | ❌ missing |
| `GET /insights/summaries/:summaryId` | ❌ missing |
| `DELETE /insights/summaries/:summaryId` | ❌ missing |
| `POST /insights/summaries/:summaryId/regenerate` | ❌ missing |

These need to be added to `server.js`, matching the DynamoDB data model and Step Functions payload format used by the Lambda API (Template 3).

**DynamoDB key pattern for summaries:**
```
PK: USER#<userId>
SK: SUMMARY#<createdAt>#<summaryId>
```

**Step Functions payload for summary:**
```json
{
  "type": "summary",
  "userId": "<userId>",
  "summaryId": "<summaryId>",
  "requestId": "<requestId>"
}
```

### Gap 3 — Missing env vars for App Runner service

The `compute_container/main.tf` does not pass `AI_ENABLED` to the container. The Node.js server needs to know whether to call Step Functions when creating a summary.

Add to `image_configuration.runtime_environment_variables`:
```hcl
AI_ENABLED = var.ai_enabled
```

Add `ai_enabled` as a variable in `variables.tf`.

### Gap 4 — Dockerfile for Node.js API

A production-ready Dockerfile is needed for `services/container_api/`. The existing `Dockerfile` in that directory needs to be reviewed and confirmed to work with the AWS App Runner port expectations (`PORT` env var, `0.0.0.0` bind address).

---

## 4. What to simplify vs Template 3

Template 3 supports `compute_mode = serverless | container | hybrid`. Template 4 removes this complexity — it is **always container**.

| Template 3 | Template 4 |
|------------|------------|
| `compute_mode` variable | Removed — always container |
| Hybrid Lambda+Container routing | Removed |
| Lambda zip cache management | Removed |
| Two-pass Terraform apply for Cognito | Same (CloudFront URL needed for callback) |
| `step-3b-build-push-container.sh` | Kept — builds + pushes image to ECR |
| Lambda API deploy | Removed — no Lambda API |
| `step-3c-deploy-backend.sh` | Simplified — targets App Runner + AI Gateway only |

---

## 5. Proposed directory structure

```
template-4-container-journal/
├── README.md
├── docs/
│   ├── Scope.md           ← this file
│   ├── Architecture.md
│   └── Setup.md
├── apps/
│   └── web/               ← React SPA (same as Template 3)
├── services/
│   ├── container_api/     ← Node.js/Express API
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── src/
│   │       └── server.js  ← add Insights endpoints
│   └── workflows/         ← Step Functions + AI Gateway Lambda (same as Template 3)
│       ├── src/
│       │   └── ai_gateway.py
│       └── statemachine/
│           └── process_entry_ai.asl.json
└── infra/
    └── terraform/
        ├── main.tf        ← no compute_mode switch, always container
        ├── variables.tf
        ├── outputs.tf
        └── modules/
            ├── auth/
            ├── db/
            ├── compute_container/  ← fix instance IAM role
            ├── api_edge/
            ├── ai_gateway/
            ├── workflow/
            └── web_hosting/
```

---

## 6. Build sequence (when implementation begins)

1. **Scaffold** — Create directory structure, copy modules from Template 3
2. **Fix compute_container** — Add App Runner instance IAM role
3. **Add Insights endpoints** — Extend `server.js` with all 5 summary endpoints
4. **Simplify Terraform** — Remove `compute_mode` logic, always container
5. **Simplify scripts** — Remove Lambda zip steps, keep container build/push
6. **Test locally** — Docker compose with DynamoDB Local
7. **Deploy to AWS** — Full setup script run
8. **Update docs** — Architecture diagram, Setup.md

---

## 7. Open decisions

| Decision | Options | Preferred |
|----------|---------|-----------|
| Container runtime | Node.js (existing) vs Python FastAPI | **Node.js** — already written |
| Container orchestration | App Runner vs ECS Fargate | **App Runner** — simpler, no VPC required |
| Step Functions AI | Lambda (reuse) vs container sidecar | **Lambda** — already works, reuse as-is |
| Auth in container | JWKS verify in Express middleware | **Same as current** — `jose` library already used |
| Local dev | Docker Compose with DynamoDB Local | **Same pattern as Template 3** |

---

## 8. Non-goals for Template 4

- VPC / private networking (App Runner public endpoint is sufficient for this template)
- Custom domain / ACM certificate (out of scope; same as Template 3)
- Blue/green deployment or canary releases
- CI/CD pipeline (manual deploy scripts only)
- Multi-region deployment
