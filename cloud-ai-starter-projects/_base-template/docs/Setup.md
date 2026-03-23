# Setup Guide — {{APP_TITLE}}

Step-by-step instructions for running locally and deploying to AWS.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker Desktop | Latest | Local dev stack |
| Node.js | 18+ | Frontend build |
| Python | 3.11+ | Backend tests (runs in Docker locally) |
| AWS CLI | v2 | Deployment |
| Terraform | 1.5+ | Infrastructure |

---

## Local Development

### Start the full local stack

```bash
make dev
```

This starts:
- **DynamoDB Local** — in-memory, port 8000
- **FastAPI** — port 8080 (`/docs` for Swagger UI)
- **React (Nginx)** — port 3000
- **Ollama** — LLM inference, port 11434 (first run downloads ~2 GB)
- **ChromaDB** — vector store for RAG, port 8001

| URL | Service |
|-----|---------|
| http://localhost:3000 | Web UI |
| http://localhost:8080/docs | API Swagger UI |
| http://localhost:11434 | Ollama |
| http://localhost:8001 | ChromaDB |

**First run:** Ollama downloads `llama3.2` (~2 GB) and `nomic-embed-text` (~275 MB). Watch progress with:

```bash
make dev-logs
```

### Other local modes

```bash
make dev-ai       # Ollama AI enrichment only (no RAG/vector search)
make dev-minimal  # CRUD only, no AI, no RAG (fastest startup)
```

### Stop

```bash
make dev-down
```

### Run tests

```bash
make test
```

### Frontend hot-reload dev server

```bash
make web-dev      # http://localhost:5173 (proxies /api to port 8080)
```

---

## AWS Setup

> Skip this section if you only need local dev.

### 1. Configure AWS credentials

You need an AWS profile named `{{APP_PREFIX}}-dev` before running any deploy commands.

**Option A — Admin IAM User (recommended, works on Free Tier)**

Create a dedicated IAM user with administrator access. This works on all account types.

> **Free Tier note:** Creating an IAM **user** is always allowed. What may trigger a plan change is creating IAM **roles** with cross-account trust (used by SSO). A plain IAM user with an access key is the simplest approach.

1. Go to **AWS Console → IAM → Users → Create User**
2. Name it `{{APP_PREFIX}}-deploy` (or any name you prefer)
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
4. Create an **Access Key** (CLI type) and copy the ID + secret
5. Run:

```bash
aws configure --profile {{APP_PREFIX}}-dev
# AWS Access Key ID:     AKIA...
# AWS Secret Access Key: ...
# Default region:        {{AWS_REGION}}
# Default output:        json
```

**Option B — Reuse existing credentials**

If you already have an IAM user with sufficient permissions, add a new profile pointing to the same key:

```bash
# Open ~/.aws/credentials and add:
[{{APP_PREFIX}}-dev]
aws_access_key_id     = <your-existing-key-id>
aws_secret_access_key = <your-existing-secret>

# Open ~/.aws/config and add:
[profile {{APP_PREFIX}}-dev]
region = {{AWS_REGION}}
output = json
```

**Option C — SSO / IAM Identity Center (teams)**

```bash
aws configure sso --profile {{APP_PREFIX}}-dev
aws sso login --profile {{APP_PREFIX}}-dev
```

### 2. Verify credentials

```bash
aws sts get-caller-identity --profile {{APP_PREFIX}}-dev
# Should return your account ID and ARN
```

### 3. Bedrock access (AI features only)

> Skip if you disabled AI during project creation.

Bedrock model access is **activated automatically on first API call** — no manual console setup required. The template uses `us-east-1` for all Bedrock calls regardless of your deploy region.

Ensure your IAM user has the `AmazonBedrockFullAccess` managed policy (included in `AdministratorAccess`).

> If AI enrichment fails silently, check CloudWatch logs for the AI Gateway Lambda — it will show the exact Bedrock error (e.g., access denied, unsupported region).

---

## Deploy to AWS

Run these in order for a first-time deployment:

```bash
# 1. Bootstrap Terraform backend (S3 bucket + DynamoDB lock table)
make bootstrap

# 2. Store secrets + user allowlist in SSM Parameter Store
#    Edit .env.users first — add your email
make secrets

# 3. Provision all infrastructure via Terraform
make infra

# 4. Deploy Lambda code + build and sync web app
make deploy

# 5. Create your admin Cognito user
make cognito-admin
```

### Iterative deploys (after first deploy)

```bash
make deploy-backend   # Lambda API + AI Gateway + Step Functions
make deploy-web       # React build + S3 sync + CloudFront invalidation
make deploy           # Both of the above
```

---

## Teardown

To delete all AWS resources (billing stops immediately after):

```bash
# Step 1: Terraform destroy
AWS_PROFILE={{APP_PREFIX}}-dev ./scripts/destroy/step-1a-terraform-destroy.sh dev

# Step 2: Delete ECR repository (images)
AWS_PROFILE={{APP_PREFIX}}-dev ./scripts/destroy/step-1b-delete-ecr-repo.sh dev

# Step 3: Delete Terraform backend (S3 + DynamoDB)
AWS_PROFILE={{APP_PREFIX}}-dev ./scripts/destroy/step-1c-delete-terraform-backend.sh dev

# Step 4: Verify everything is gone
AWS_PROFILE={{APP_PREFIX}}-dev ./scripts/destroy/step-1d-verify-destroy.sh dev
```

---

## Free Tier Notes

Most services used by this template have free tier allowances:

| Service | Free tier |
|---------|----------|
| DynamoDB | 25 GB storage, 25 WCU/RCU |
| Lambda | 1M requests/month |
| S3 | 5 GB storage |
| CloudFront | 1 TB data transfer |
| Cognito | 50,000 MAUs |
| API Gateway | 1M API calls/month |
| Bedrock | **Not included** — pay per token |

> To avoid Bedrock charges, disable AI features during project creation or set `LLM_PROVIDER=ollama` locally.
