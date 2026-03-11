# Template 3 TODO (Manual Setup + Validation)

## Infrastructure
- [ ] Fill `dev.tfvars` and choose compute mode.
- [ ] Terraform init/plan/apply succeeds.
- [ ] Capture outputs for API and Cognito.

## Container Mode
- [ ] Build and push container image to ECR.
- [ ] Set `container_image_uri` and re-apply Terraform.
- [ ] Verify App Runner health and API edge integration.

## Web
- [ ] Configure `apps/web/.env` from Terraform outputs.
- [ ] Run web app locally and verify auth flow.

## Validation
- [ ] Run full runbook smoke tests for selected mode.
- [ ] If hybrid mode, test both lambda and container paths.
