# AWS Account and Terraform Setup Guide (CLI-First)

This guide is optimized for CLI usage. Use AWS Console only where CLI is not possible.

## 1) One-time AWS Account Setup

## 1.1 UI (required, minimal)
The following must be done in AWS Console:
1. Create/sign in to AWS account.
2. Configure billing alerts and MFA on root user.
3. Enable Bedrock model access for your target region and model (for example `amazon.nova-lite-v1:0`).

Everything else below is CLI-first.

## 1.2 CLI tooling install
- Install AWS CLI v2
- Install Terraform >= 1.6

Verify:
```bash
aws --version
terraform version
```

## 1.3 Configure CLI credentials (preferred)
If your org supports IAM Identity Center (SSO):
```bash
aws configure sso
aws sso login --profile journal-dev
aws sts get-caller-identity --profile journal-dev
```

If using access keys:
```bash
aws configure --profile journal-dev
aws sts get-caller-identity --profile journal-dev
```

Set default profile for this shell:
```bash
export AWS_PROFILE=journal-dev
```

## 2) Create least-privilege deploy role/user (CLI preferred)
Use your platform bootstrap identity to create a deploy identity with permissions for:
- Cognito
- API Gateway v2
- Lambda
- IAM (for Lambda/StepFunctions roles/policies)
- DynamoDB
- Step Functions
- S3
- CloudWatch Logs
- Bedrock Runtime

If your org already has a deploy role, reuse it.

## 3) Create Terraform remote state resources (CLI preferred)

Choose unique names:
- state bucket: `journal-tfstate-<account-id>-<region>`
- lock table: `journal-tflock`

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
STATE_BUCKET="journal-tfstate-${ACCOUNT_ID}-${REGION}"
LOCK_TABLE="journal-tflock"

aws s3api create-bucket \
  --bucket "$STATE_BUCKET" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION"

aws s3api put-bucket-versioning \
  --bucket "$STATE_BUCKET" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket "$STATE_BUCKET" \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws dynamodb create-table \
  --table-name "$LOCK_TABLE" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION"
```

## 4) Configure this template for dev

From repo root:
```bash
cd cloud-ai-starter-projects/template-1-aws-journal/infra/terraform
```

Update dev vars:
- `environments/dev/dev.tfvars`
  - `cognito_domain_prefix` must be globally unique
  - `aws_region` should match Bedrock-enabled region

## 5) Terraform init/plan/apply

## 5.1 Local state (quick start)
```bash
terraform init
terraform plan -var-file=environments/dev/dev.tfvars
terraform apply -var-file=environments/dev/dev.tfvars
```

## 5.2 Remote state (recommended)
Create backend config file from example:
```bash
cp backend.s3.tfbackend.example backend.dev.tfbackend
```

Edit `backend.dev.tfbackend` values (`bucket`, `region`, `dynamodb_table`, `key`), then:
```bash
terraform init -reconfigure -backend-config=backend.dev.tfbackend
terraform plan -var-file=environments/dev/dev.tfvars
terraform apply -var-file=environments/dev/dev.tfvars
```

## 6) Capture outputs for web app
```bash
terraform output
terraform output -raw api_base_url
terraform output -raw cognito_domain
terraform output -raw cognito_client_id
terraform output -raw site_url
```

## 7) Configure and run web app locally

```bash
cd ../../apps/web
cp .env.example .env
```

Set in `.env`:
- `VITE_API_BASE_URL` from `api_base_url`
- `VITE_COGNITO_DOMAIN` from `cognito_domain`
- `VITE_COGNITO_CLIENT_ID` from `cognito_client_id`
- `VITE_COGNITO_REDIRECT_URI=http://localhost:5173/callback`
- `VITE_COGNITO_LOGOUT_URI=http://localhost:5173/`

Run:
```bash
npm install
npm run dev
```

## 8) Validate Bedrock access (CLI preferred)
```bash
aws bedrock list-foundation-models --region us-east-1 --output table
```

If model invocation fails but model is listed, verify model access is enabled in Console.

## 9) Destroy environment
```bash
cd ../infra/terraform
terraform destroy -var-file=environments/dev/dev.tfvars
```

If using remote backend, keep state bucket/lock table for future runs.
