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
make new-project DEFAULTS=true APP=first-my-app 
```

### Custom output path (standalone project outside this repo)

```bash
make new-project APP=budget OUT=~/projects/budget
```

This creates a fully standalone project at the given path — useful when you want a separate git repo.

### What happens

1. Copies `_base-template/` → target directory
2. Replaces all `{{PLACEHOLDER}}` strings with your values
3. Prompts to enable/disable features (AI, RAG, Admin, CSV Import, Insights)
4. Removes files for disabled features
5. Generates `.env.docker` and `.env.users`
6. Runs `npm install` for the web app
7. Creates `docs/IMPLEMENTATION_CHECKLIST.md`

### Configuration prompts

| Setting | What it controls | Default | Example |
|---------|-----------------|---------|---------|
| `APP_PREFIX` | AWS resource names, table names, container names | (required) | `budget` |
| `APP_TITLE` | Browser title, UI brand name | Capitalized prefix | `Budget Tracker` |
| `AWS_REGION` | Deployment region | `ca-central-1` | `us-east-1` |
| `AWS_PROFILE` | AWS CLI profile for deployments | `{prefix}-dev` | `my-app-dev` |
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

**Default** — inside this repo (gitignored):

```
aws-starter-projects/
├── cloud-ai-starter-projects/
│   └── _base-template/          ← source template (never edit generated projects here)
├── generated/
│   ├── budget/                  ← make new-project APP=budget
│   └── tracker/                 ← make new-project APP=tracker
├── Makefile                     ← run `make new-project` from here
└── .gitignore                   ← generated/ is gitignored
```

**Custom** — anywhere on disk:

```bash
make new-project APP=budget OUT=~/projects/budget
# Creates ~/projects/budget/ as a standalone project
# You can `cd ~/projects/budget && git init` to make it its own repo
```

---

## 2. Run Locally

```bash
cd generated/budget

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
cd generated/budget

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
cd generated/budget

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
rm -rf generated/budget
```

That's it. Docker images will be cleaned up on next `docker system prune`.

### Previously deployed to AWS

Run the destroy scripts **before** deleting local files:

```bash
cd generated/budget

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
rm -rf generated/budget
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

## 6. AWS Configuration

> Complete this section before deploying. Not needed for local dev.

Choose the option that matches your AWS account type:

### Option A: Admin IAM User (AWS Free Tier / personal learning)

Create a dedicated **IAM user** with administrator access. This works on all account types including the Free Tier.

> **Free Tier note:** Creating an IAM **user** is allowed and free. What may trigger a pay-as-you-go prompt is creating IAM **roles** with cross-account trust policies (used by SSO/Identity Center). A plain IAM user with an access key is the simplest approach and always available.

1. Go to **AWS Console → IAM → Users → Create User**
2. Name it something like `{{APP_PREFIX}}-deploy` (or any name you prefer)
3. Attach the **AdministratorAccess** managed policy (or the scoped list in Option B below)
4. Create an **Access Key** (CLI type) and copy the ID + secret
5. Configure the CLI:

```bash
aws configure --profile {{APP_PREFIX}}-dev
# AWS Access Key ID:     AKIA...
# AWS Secret Access Key: wJal...
# Default region:        ca-central-1
# Default output:        json
```

**Free Tier considerations:**
- Most services this template uses (DynamoDB, Lambda, S3, CloudFront, Cognito, API Gateway) have a free tier allowance
- Bedrock is **not** included in the free tier — AI features will incur charges
- You can disable AI/RAG features during project creation to stay within free tier
- Monitor costs at **AWS Console → Billing → Free Tier** dashboard

### Option B: Scoped IAM User (personal projects, pay-as-you-go accounts)

Same as Option A but with least-privilege policies instead of AdministratorAccess:

1. Go to **AWS Console → IAM → Users → Create User**
2. Name it something like `{{APP_PREFIX}}-deploy`
3. Attach these managed policies:
   - `AmazonDynamoDBFullAccess`
   - `AWSLambda_FullAccess`
   - `AmazonS3FullAccess`
   - `AmazonCognitoPowerUser`
   - `IAMFullAccess`
   - `CloudFrontFullAccess`
   - `AmazonAPIGatewayAdministrator`
   - `AmazonECR_FullAccess`
   - `AWSStepFunctionsFullAccess`
   - `AmazonSSMFullAccess`
4. Create an **Access Key** (CLI type) and note the ID + secret
5. Configure the CLI:

```bash
aws configure --profile {{APP_PREFIX}}-dev
# AWS Access Key ID:     AKIA...
# AWS Secret Access Key: wJal...
# Default region:        ca-central-1
# Default output:        json
```

### Option C: IAM Identity Center / SSO (recommended for teams)

Best for organizations with multiple developers or AWS accounts:

```bash
aws configure sso --profile {{APP_PREFIX}}-dev
# SSO start URL:     https://your-org.awsapps.com/start
# SSO Region:        us-east-1
# Account:           123456789012
# Role:              AdministratorAccess (or a scoped role)
# CLI default region: ca-central-1
# CLI output:        json
```

Login before running any commands:

```bash
aws sso login --profile {{APP_PREFIX}}-dev
```

### Which option should I pick?

| Situation | Recommended option |
|-----------|-------------------|
| AWS Free Tier / personal learning | **Option A** — Admin IAM user |
| Personal project, pay-as-you-go account | **Option B** — Scoped IAM user |
| Team / organization / multiple accounts | **Option C** — IAM Identity Center |
| Production workload | **Option C** — with least-privilege role |

### Verify credentials work

```bash
aws sts get-caller-identity --profile {{APP_PREFIX}}-dev
# Should show your account ID and ARN
```

### Bedrock access (required for AI features)

Bedrock LLMs and Titan Embeddings V2 are **only available in certain regions** (us-east-1, us-west-2, eu-west-1). The template defaults Bedrock calls to `us-east-1` regardless of your deploy region.

Bedrock model access is **activated automatically on first API call** — no manual setup required. The template uses `us-east-1` for all Bedrock calls regardless of your deploy region.

> If AI enrichment fails silently, verify that your IAM user has `AmazonBedrockFullAccess` (or equivalent) and that you're calling from a supported region (`us-east-1`, `us-west-2`, `eu-west-1`).

### Environment variables reference

| Variable | Where set | Purpose |
|----------|-----------|---------|
| `AWS_PROFILE` | Shell / Makefile | Which AWS credentials to use |
| `AWS_REGION` | Terraform vars | Where to deploy infrastructure |
| `BEDROCK_REGION` | Terraform → Lambda env | Where Bedrock calls go (default: `us-east-1`) |
| `TABLE_NAME` | Terraform → Lambda env | DynamoDB table name |
| `ADMIN_EMAILS` | SSM → Lambda env | Comma-separated admin emails |
| `LLM_PROVIDER` | Lambda env / docker-compose | AI provider: `bedrock`, `groq`, `ollama`, `openai` |
| `GROQ_API_KEY` | SSM → Lambda env | Groq API key (if using Groq) |

---

## 7. Deploy to AWS

### First-time setup

```bash
cd generated/budget

# 1. Create Terraform backend (S3 + DynamoDB lock table)
make bootstrap

# 2. Edit user allowlist
cp .env.users.example .env.users
# Add your email(s), one per line. Prefix with "admin:" for admin access.

# 3. Store secrets in SSM Parameter Store
make secrets

# 4. Deploy all infrastructure
make infra

# 5. Deploy code (Lambda + frontend)
make deploy

# 6. Create admin Cognito user
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

## 8. Multiple Projects Side by Side

Each project runs independently. Default ports are the same, so **only run one project at a time** locally, or change the ports:

Edit `docker/docker-compose.yml` in the second project:

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
| Delete project | `rm -rf generated/budget` | Repo root |
| List projects | `make help` | Repo root |
