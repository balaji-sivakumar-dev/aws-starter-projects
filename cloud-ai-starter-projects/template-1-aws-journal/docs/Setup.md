# Setup

CLI-first setup and runbook in one place.

## Prereqs
- AWS account with root MFA, billing alerts, and budgets configured.
- Bedrock model access enabled if you plan to use AI features.
- Tools: AWS CLI v2, Terraform >= 1.6, Node + npm.

## Configure AWS CLI
SSO:
```bash
aws configure sso
aws sso login --profile journal-dev
aws sts get-caller-identity --profile journal-dev
```

Access keys:
```bash
aws configure --profile journal-dev
aws sts get-caller-identity --profile journal-dev
```

Set default profile:
```bash
export AWS_PROFILE=journal-dev
```

## Bootstrap Terraform backend
```bash
AWS_PROFILE=journal-dev ./scripts/setup/step-2-bootstrap-terraform-backend.sh
AWS_PROFILE=journal-dev ./scripts/setup/step-2b-create-backend-file.sh dev
```

## Configure environment
Update `infra/terraform/environments/dev/dev.tfvars`:
- `cognito_domain_prefix` must be globally unique
- `aws_region` should be a Bedrock-enabled region
- `web_enable_cloudfront` should be `true` for HTTPS + Cognito redirects

## Apply infrastructure (exports `.env`)
```bash
AWS_PROFILE=journal-dev ./scripts/setup/step-3a-terraform-apply.sh dev
```

Notes:
- The web app uses the current browser origin for Cognito redirect/logout URLs.
- Terraform now allows both localhost and the deployed site URL for callbacks.

## Deploy web app to S3 (CloudFront enabled)
Deploy:
```bash
AWS_PROFILE=journal-dev ./scripts/setup/step-4a-deploy-web-to-s3.sh dev
```

## Run locally
```bash
cd apps/web
npm install
npm run dev
```

## Smoke checks
1. `GET /health` returns 200.
2. Open web app and login via Cognito Hosted UI.
3. Confirm profile data loads from `GET /me`.
4. Create entry and verify it appears in list/detail.
5. Edit entry and verify updates persist.
6. Trigger AI (`POST /entries/{entryId}/ai`).
7. Refresh detail until `aiStatus` is `COMPLETE` or `FAILED`.
8. Validate `summary` and `tags` appear when complete.

## Destroy
```bash
AWS_PROFILE=journal-dev ./scripts/destroy/step-1a-terraform-destroy.sh dev
AWS_PROFILE=journal-dev ./scripts/destroy/step-1b-delete-terraform-backend.sh
AWS_PROFILE=journal-dev ./scripts/destroy/step-1c-verify-destroy.sh dev
```
