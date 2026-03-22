# Template Usage Guide

How to create, run, manage, and remove projects from the base template.

---

## Prerequisites

- **Docker Desktop** — running (for local dev)
- **Node.js 18+** — for frontend build
- **Python 3.11+** — for backend tests (optional locally, runs in Docker)
- **AWS CLI v2** — for deployment (not needed for local dev)
- **Terraform 1.5+** — for infrastructure (not needed for local dev)

---

## 1. Create a New Project

All projects are created from the repo root.

### Interactive mode (prompts for each setting)

```bash
make new-project APP=budget
```

### Quick mode (use all defaults)

```bash
make new-project APP=budget DEFAULTS=true
```

### What happens

1. Copies `_base-template/` → `cloud-ai-starter-projects/template-budget/`
2. Replaces all `{{PLACEHOLDER}}` strings with your values
3. Prompts to enable/disable features (AI, RAG, Admin, CSV Import, Insights)
4. Removes files for disabled features
5. Generates `.env.docker` and `.env.users`
6. Runs `npm install` for the web app
7. Creates an `IMPLEMENTATION_CHECKLIST.md`

### Configuration prompts

| Setting | What it controls | Default | Example |
|---------|-----------------|---------|---------|
| `APP_PREFIX` | AWS resource names, table names, container names | (required) | `budget` |
| `APP_TITLE` | Browser title, UI brand name | Capitalized prefix | `Budget Tracker` |
| `AWS_REGION` | Deployment region | `ca-central-1` | `us-east-1` |
| `AWS_PROFILE` | AWS CLI profile for deployments | `{prefix}-dev` | `budget-dev` |
| `ENABLE_AI` | AI enrichment (summarize + tag items) | `y` | `n` |
| `ENABLE_RAG` | RAG pipeline (chat with your data) | `y` | `n` |
| `ENABLE_ADMIN` | Admin dashboard + audit logs | `y` | `n` |
| `ENABLE_CSV_IMPORT` | CSV bulk import UI | `y` | `n` |
| `ENABLE_INSIGHTS` | Period summaries (weekly/monthly) | `y` | `n` |

### Naming rules

- `APP_PREFIX` must be **lowercase letters, numbers, and hyphens** only
- 2–21 characters, must start with a letter
- Examples: `budget`, `my-app`, `tracker2`
- Bad: `Budget` (uppercase), `1app` (starts with number), `a` (too short)

### Where projects go

All generated projects land in:

```
aws-starter-projects/
├── cloud-ai-starter-projects/
│   ├── _base-template/          ← source template (don't edit generated projects here)
│   ├── template-budget/         ← your generated project
│   ├── template-tracker/        ← another project
│   └── template-3-.../          ← existing Reflect app
├── Makefile                     ← run `make new-project` from here
└── CLAUDE.md
```

The destination is always `cloud-ai-starter-projects/template-{APP_PREFIX}/`. This is not configurable — it keeps all projects in a consistent location.

---

## 2. Run Locally

```bash
cd cloud-ai-starter-projects/template-budget

# Start all services (DynamoDB + API + Web)
make dev
```

This runs `docker compose up -d` and starts three containers:

| Container | URL | Purpose |
|-----------|-----|---------|
| `budget-dynamodb` | `localhost:8000` | DynamoDB Local (in-memory) |
| `budget-api` | `localhost:8080` | FastAPI backend |
| `budget-web` | `localhost:3000` | React SPA via Nginx |

### Verify it's working

```bash
# API health check
curl http://localhost:8080/health
# → {"status":"ok"}

# Create an item
curl -X POST http://localhost:8080/entries \
  -H "X-User-Id: dev-user" \
  -H "Content-Type: application/json" \
  -d '{"title":"My first item","body":"Hello world"}'

# List items
curl http://localhost:8080/entries -H "X-User-Id: dev-user"

# Open web UI
open http://localhost:3000
```

### View logs

```bash
# All containers
docker compose logs -f

# API only
docker compose logs -f api
```

### Rebuild after code changes

```bash
# Rebuild and restart API only
docker compose up --build api -d

# Rebuild everything
docker compose up --build -d
```

### Frontend development (hot reload)

For faster frontend iteration, run Vite's dev server instead of the Docker web container:

```bash
make web-dev
# → http://localhost:5173 (hot reloads on save)
```

Note: The Vite dev server proxies `/api/*` to `localhost:8080`, so the API container must still be running.

---

## 3. Stop the Project

```bash
cd cloud-ai-starter-projects/template-budget

# Stop containers (keeps images and volumes)
make dev-down

# Or equivalently:
docker compose down
```

To also remove the built images:

```bash
docker compose down --rmi local
```

---

## 4. Run Tests

```bash
cd cloud-ai-starter-projects/template-budget

# Create virtualenv (first time only)
python3 -m venv services/api/.venv
services/api/.venv/bin/pip install -r services/api/requirements.txt -r services/api/requirements-dev.txt

# Run tests
make test

# Or directly:
services/api/.venv/bin/pytest services/api/tests/ -v
```

Tests use `moto` to mock DynamoDB — no running containers needed.

---

## 5. Delete a Project

If you no longer need a generated project:

### Local only (never deployed to AWS)

```bash
# From repo root
rm -rf cloud-ai-starter-projects/template-budget
```

That's it. Docker images will be cleaned up on next `docker system prune`.

### Previously deployed to AWS

Run the destroy scripts **before** deleting local files:

```bash
cd cloud-ai-starter-projects/template-budget

# Step 1: Terraform destroy (removes all AWS resources)
make destroy

# Step 2: Delete ECR repository
bash scripts/destroy/step-1b-delete-ecr-repo.sh dev

# Step 3: Delete Terraform backend (S3 bucket + DynamoDB lock table)
bash scripts/destroy/step-1c-delete-terraform-backend.sh dev

# Step 4: Verify everything is gone
bash scripts/destroy/step-1d-verify-destroy.sh dev

# Step 5: Remove local files
cd ../..
rm -rf cloud-ai-starter-projects/template-budget
```

### Clean up Docker resources

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Nuclear option: remove all unused Docker resources
docker system prune -a
```

---

## 6. Deploy to AWS

> This section is for when you're ready to go beyond local dev.

### First-time setup

```bash
cd cloud-ai-starter-projects/template-budget

# 1. Configure AWS CLI profile (see scripts/setup/step-1-aws-configure.md)

# 2. Create Terraform backend (S3 + DynamoDB lock table)
make bootstrap

# 3. Edit user allowlist
cp .env.users.example .env.users
# Add your email(s), one per line. Prefix with "admin:" for admin access.

# 4. Store secrets in SSM Parameter Store
make secrets

# 5. Deploy all infrastructure
make infra

# 6. Deploy code (Lambda + frontend)
make deploy

# 7. Create admin Cognito user
make cognito-admin
```

### Iterative deploys (after first setup)

```bash
# Backend only (Lambda API + AI Gateway + Step Functions)
make deploy-backend

# Frontend only (React → S3 → CloudFront invalidation)
make deploy-web

# Both
make deploy

# Just the API Lambda
make deploy-api
```

---

## 7. Multiple Projects Side by Side

Each project runs independently. Default ports are the same, so **only run one project at a time** locally, or change the ports:

Edit `docker-compose.yml` in the second project:

```yaml
# Change ports to avoid conflicts
ports:
  - "3001:80"    # web (was 3000)
  - "8081:8080"  # api (was 8080)
  - "8001:8000"  # dynamodb (was 8000)
```

---

## Quick Reference

| Task | Command | Where |
|------|---------|-------|
| Create project | `make new-project APP=budget` | Repo root |
| Start local | `make dev` | Project dir |
| Stop local | `make dev-down` | Project dir |
| View logs | `docker compose logs -f` | Project dir |
| Rebuild API | `docker compose up --build api -d` | Project dir |
| Run tests | `make test` | Project dir |
| Deploy to AWS | `make deploy` | Project dir |
| Delete project | `rm -rf cloud-ai-starter-projects/template-budget` | Repo root |
| List projects | `make help` | Repo root |
