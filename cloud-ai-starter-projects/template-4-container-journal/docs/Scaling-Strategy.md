# Scaling Strategy — Lambda vs Container vs Microservices

> **Status: Design phase**
> Last updated: 2026-03-14

---

## 1. The real question

The concern isn't "Lambda vs Container" — it's **how to organize growing complexity without drowning in operational overhead**.

A Curriculum app might have:
- Content management (courses, modules, materials)
- Content processing (parse, chunk, embed)
- Exam engine (generate MCQs, theory, answer-based; grade; track)
- Learning path engine (analyze performance, recommend next steps)
- RAG/search (query course content semantically)
- Analytics (progress dashboards, performance trends)
- User management (teachers, students, cohorts, permissions)

That's 7 domains. Each has CRUD + business logic + possibly AI. If each domain has 8-10 endpoints, that's 50-70 API routes. The question: how do you deploy and manage that?

---

## 2. Three deployment models compared

### Model A — One Lambda per route (50+ functions)

```
API Gateway
├── GET  /courses         → lambda-get-courses
├── POST /courses         → lambda-create-course
├── GET  /courses/{id}    → lambda-get-course
├── POST /exams/generate  → lambda-generate-exam
├── POST /exams/{id}/grade → lambda-grade-exam
├── ...50 more...
```

| Pros | Cons |
|------|------|
| Each function scales independently | 50+ Lambda functions to deploy, monitor, debug |
| Minimal blast radius per deploy | IAM roles per function = permission sprawl |
| Fine-grained concurrency limits | Terraform becomes massive (50 modules) |
| | Cold starts multiply (each function warms independently) |
| | Shared code (DB layer, auth) duplicated across ZIPs |

**Verdict: Don't do this.** This is the "nano-service" anti-pattern. Operational cost far exceeds the scaling benefit for an app this size.

---

### Model B — Fat Lambda (few functions, many routes) ← RECOMMENDED START

```
API Gateway
├── /courses/*     → lambda-content-api    (handles all content routes)
├── /exams/*       → lambda-exam-api       (handles all exam routes)
├── /analytics/*   → lambda-analytics-api  (handles all analytics routes)
├── /rag/*         → lambda-rag-api        (handles all RAG routes)
└── /users/*       → lambda-content-api    (shares with content domain)
```

**3-5 Lambda functions**, each a "fat Lambda" that handles all routes for a domain. Each Lambda contains a full Python handler (or FastAPI via Mangum) with internal routing.

| Pros | Cons |
|------|------|
| 3-5 functions to manage (not 50) | Slightly larger deployment packages |
| Shared code bundled per domain | One domain's bug can crash its Lambda |
| Cold starts minimized (fewer unique functions) | Can't scale one route independently of others in same Lambda |
| Same near-zero cost at idle | Package size grows as domain logic grows |
| Matches Template 3's proven pattern | |
| Easy to split later if needed | |

**This is what Template 3 already does** — one Lambda (`handler.py`) handles all routes. The evolution is to split by domain when complexity demands it.

**How it works internally**:

```python
# lambda-content-api/handler.py
def handler(event, context):
    path = event["rawPath"]
    method = event["requestContext"]["http"]["method"]

    if path.startswith("/courses"):
        return content_handlers.route(method, path, event)
    elif path.startswith("/users"):
        return user_handlers.route(method, path, event)
    else:
        return {"statusCode": 404}
```

Or use the Core + Adapters pattern (FastAPI via Mangum) where each domain is a FastAPI router:

```python
# Each domain is a separate router file
from content.routes import router as content_router
from exams.routes import router as exam_router

app = FastAPI()
app.include_router(content_router, prefix="/courses")
app.include_router(exam_router, prefix="/exams")

# Lambda entry point
handler = Mangum(app)
```

---

### Model C — Container microservices (ECS Fargate / App Runner)

```
ALB / API Gateway
├── /courses/*     → ECS Service: content-api (2 tasks)
├── /exams/*       → ECS Service: exam-api (2 tasks)
├── /analytics/*   → ECS Service: analytics-api (1 task)
├── /rag/*         → ECS Service: rag-api (2 tasks)
```

Each service is a Docker container with its own ECS task definition, auto-scaling, and deployment pipeline.

| Pros | Cons |
|------|------|
| Independent scaling per service | Minimum cost ~$7-15/mo per service (always-on) |
| Independent deployments | 4 services = $28-60/mo minimum even at 0 users |
| Different languages per service if needed | ECS/Fargate Terraform is complex (task defs, services, ALB rules, security groups, VPC) |
| Long-running connections (WebSockets) | Need service discovery for inter-service calls |
| No cold starts | Container image builds + ECR pushes add deploy time |
| Team ownership boundaries (future) | Overkill for solo/small team |

**Verdict: Too early.** This makes sense when you have separate teams, need independent deploy cadences, or have services with very different scaling profiles. For a solo developer building an MVP, the operational overhead isn't justified.

---

## 3. Recommended evolution path

```
Phase 1 (MVP)           Phase 2 (Growth)           Phase 3 (Scale)
─────────────          ──────────────────          ─────────────────
Single Fat Lambda  →   3-5 Domain Lambdas    →    Container Microservices
(all routes)           (split by domain)           (split by team/scale need)

1 deployment unit      3-5 deployment units        N independent services
~$0/mo at idle         ~$0/mo at idle              ~$30-100/mo minimum
Minutes to deploy      Minutes to deploy           CI/CD pipeline needed

Template 3 pattern     Natural evolution            Only when needed
```

### When to move from Phase 1 → Phase 2:
- Single Lambda deployment package exceeds 50 MB (Lambda limit: 250 MB unzipped)
- Deploy frequency differs between domains (exam engine changes daily, content API is stable)
- One domain's errors shouldn't affect another
- Cold start time becomes noticeable (> 3 seconds due to package size)

### When to move from Phase 2 → Phase 3:
- Multiple developers/teams own different domains
- A specific service needs persistent connections (WebSockets for real-time exam)
- A service needs different scaling characteristics (RAG queries are CPU-heavy, CRUD is light)
- Container-specific features needed (GPU for local ML, large memory for embedding)

---

## 4. Code organization — Monorepo with domain modules

Regardless of deployment model, the **code structure** stays the same. This is the key insight: organize code by domain, deploy as appropriate.

```
curriculum-app/
├── domains/
│   ├── content/                    ← Course + module management
│   │   ├── handlers.py             ← Business logic
│   │   ├── models.py               ← Data models
│   │   ├── repository.py           ← DynamoDB access
│   │   └── routes.py               ← API routes (FastAPI router)
│   │
│   ├── exams/                      ← Exam generation + grading
│   │   ├── handlers.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── routes.py
│   │   └── prompts/                ← LLM prompt templates
│   │       ├── generate_mcq.py
│   │       ├── generate_theory.py
│   │       └── grade_answer.py
│   │
│   ├── learning/                   ← Performance analysis + recommendations
│   │   ├── handlers.py
│   │   ├── analytics.py
│   │   └── routes.py
│   │
│   └── rag/                        ← Semantic search over course materials
│       ├── handlers.py
│       ├── retriever.py
│       └── routes.py
│
├── platform/                       ← Shared infrastructure (from Template 4)
│   ├── auth/
│   ├── db/
│   ├── llm/
│   ├── embedding/
│   └── file_processing/
│
├── adapters/
│   ├── lambda_single/              ← Phase 1: all domains in one Lambda
│   │   └── handler.py
│   ├── lambda_split/               ← Phase 2: one Lambda per domain
│   │   ├── content_handler.py
│   │   ├── exam_handler.py
│   │   └── rag_handler.py
│   └── fastapi/                    ← Phase 3: container deployment
│       └── app.py
│
├── infra/terraform/
│   ├── main.tf                     ← Switch between deployment modes
│   └── modules/                    ← Reusable Terraform modules
│
└── tests/
    ├── content/
    ├── exams/
    └── rag/
```

**The critical insight**: The `domains/` folder structure doesn't change when you move from Phase 1 → 2 → 3. Only the `adapters/` layer changes. This is the Core + Adapters pattern from Template 3 taken to its logical conclusion.

### Phase 1 adapter (single Lambda):
```python
# adapters/lambda_single/handler.py
from domains.content.routes import router as content_router
from domains.exams.routes import router as exam_router
from domains.learning.routes import router as learning_router
from domains.rag.routes import router as rag_router

app = FastAPI()
app.include_router(content_router, prefix="/courses")
app.include_router(exam_router, prefix="/exams")
app.include_router(learning_router, prefix="/analytics")
app.include_router(rag_router, prefix="/rag")

handler = Mangum(app)
```

### Phase 2 adapter (split Lambdas):
```python
# adapters/lambda_split/exam_handler.py
from domains.exams.routes import router as exam_router

app = FastAPI()
app.include_router(exam_router, prefix="/exams")

handler = Mangum(app)
```

Same domain code, different wiring. Zero refactoring.

---

## 5. Multi-repo vs monorepo

| Approach | When to use | Trade-offs |
|----------|-------------|------------|
| **Monorepo (single repo)** | Solo developer, MVP, shared platform code | Simpler CI, shared types, atomic changes across domains |
| **Monorepo + packages** | Small team, domains stabilizing | Each domain is a package, shared via workspace (pip/npm) |
| **Multi-repo** | Multiple teams, independent deploy cadences | Need package registry, versioned interfaces, more CI complexity |

**Recommendation**: Start monorepo. The platform (`platform/`) and all domains live together. When a domain grows large enough to justify its own team and deploy cadence, extract it to its own repo and consume the platform as a versioned package.

**Extraction signal**: If you find yourself saying "I want to deploy the exam engine without touching content management," it's time to split.

---

## 6. Terraform scaling

As you add domains, Terraform grows too. Here's how to keep it manageable:

### Phase 1 (single Lambda):
```hcl
# main.tf — same as Template 3
module "compute_lambda" {
  source     = "./modules/compute_lambda"
  source_dir = "../../services/api/src"
  # One Lambda handles everything
}
```

### Phase 2 (split Lambdas):
```hcl
# main.tf — one module call per domain Lambda
module "content_lambda" {
  source     = "./modules/compute_lambda"
  source_dir = "../../domains/content"
  function_name = "${local.prefix}-content-api"
}

module "exam_lambda" {
  source     = "./modules/compute_lambda"
  source_dir = "../../domains/exams"
  function_name = "${local.prefix}-exam-api"
}

# API Gateway routes split by prefix
module "api_edge" {
  lambda_routes = {
    content = { route_key = "ANY /courses/{proxy+}", lambda_arn = module.content_lambda.arn }
    exams   = { route_key = "ANY /exams/{proxy+}",   lambda_arn = module.exam_lambda.arn }
  }
}
```

The `compute_lambda` module is reused — just instantiated multiple times with different source directories. Same module, different inputs.

---

## 7. Curriculum app — domain complexity map

| Domain | Complexity | AI/RAG intensity | Recommended phase |
|--------|-----------|-------------------|-------------------|
| Content management | Medium | Low (CRUD) | Phase 1 |
| Content processing | Medium | High (parse, chunk, embed) | Phase 1 (async via SFN) |
| Exam generation | High | Very high (LLM-generated questions) | Phase 1, split in Phase 2 |
| Exam grading | High | High (AI grading for theory/answer-based) | Phase 1, split in Phase 2 |
| Learning paths | High | High (performance analysis, recommendations) | Phase 2 |
| RAG search | Medium | Very high (embedding + retrieval) | Phase 1 |
| Analytics | Medium | Low (aggregation queries) | Phase 2 |
| User management | Low | None | Phase 1 (reuse platform auth) |

**Estimate: 6-8 FastAPI routers, 30-50 endpoints, deployable as 1-3 Lambda functions initially.**

---

## 8. Decision summary

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Start with Lambda or Container? | **Lambda (Fat Lambda)** | Near-zero cost, proven in Template 3, split later |
| How many Lambda functions? | **1 initially, split to 3-5 when complexity demands** | Each domain is a FastAPI router, compose into 1 or many |
| Monorepo or multi-repo? | **Monorepo** | Solo developer, shared platform code, atomic changes |
| When to add containers? | **When a service needs persistent connections or GPU** | RAG with large models, real-time exam features |
| When to split repos? | **When a domain gets its own team or deploy cadence** | Not before — premature splitting adds overhead |
| Code organization? | **Domain modules + adapter layer** | Domain code is deployment-agnostic; adapters wire to Lambda/FastAPI/container |
