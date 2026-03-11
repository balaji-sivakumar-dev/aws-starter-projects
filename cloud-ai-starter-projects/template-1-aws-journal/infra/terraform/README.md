# Terraform Root

This root composes platform and domain modules for Template 1.

## Platform Modules
- `s3_spa_hosting`: static site bucket (CloudFront optional)
- `auth_cognito`: user pool + app client + hosted UI domain
- `api_gateway_http`: HTTP API routes + JWT authorizer + Lambda integrations
- `lambda`: reusable Lambda packaging/runtime/role module

## Domain Modules
- `dynamodb`: single-table Journal store (`PK`, `SK`)
- `step_functions`: ProcessEntryAI workflow state machine

## Local and Remote State
- Local backend is default for first-run simplicity.
- Remote state placeholder file: `backend.s3.tfbackend.example`.

## Dev Usage
```bash
cd infra/terraform
terraform init
terraform plan -var-file=environments/dev/dev.tfvars
terraform apply -var-file=environments/dev/dev.tfvars
```
