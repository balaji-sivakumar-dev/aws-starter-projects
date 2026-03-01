# Setup

## Local Prerequisites
- Terraform >= 1.6
- AWS CLI configured (`aws configure` / named profile)
- Python 3.11+ for local checks
- Node.js 20+ and npm (for React SPA)

## AWS Prerequisites
Set up AWS account access now, before deployment tests:
- IAM credentials/profile with permission for Cognito, API Gateway v2, Lambda, DynamoDB, Step Functions, S3, CloudWatch, Bedrock.
- Bedrock access granted for configured `BEDROCK_MODEL_ID` in the selected region.

## Terraform (Dev)
```bash
cd infra/terraform
terraform init
terraform plan -var-file=environments/dev/dev.tfvars
terraform apply -var-file=environments/dev/dev.tfvars
```

## Web App (Local)
```bash
cd apps/web
cp .env.example .env
# fill values from terraform outputs
npm install
npm run dev
```

## Remote State (Optional)
- Copy `backend.s3.tfbackend.example` to your own backend config values and run `terraform init -backend-config=<file>`.
