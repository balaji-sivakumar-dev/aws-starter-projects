# Template 1 - AWS Serverless Journal Starter Kit (Terraform)

This project is a new reusable template for Template 1.

Status: Template 1 implementation complete. CRUD validated in AWS dev on March 5, 2026; AI workflow pending Bedrock enablement.

Docs index:
- `docs/Setup.md` — setup + runbook
- `docs/Architecture.md` — platform/domain layout
- `docs/Specs.md` — API, data model, AI workflow
- `docs/Implementation-Checklist.md` — implementation + testing checklist

## Scripts (CLI-first)
Run from repo root:
```bash
AWS_PROFILE=journal-dev ./scripts/setup/step-1-aws-configure.md
AWS_PROFILE=journal-dev ./scripts/setup/step-2-bootstrap-terraform-backend.sh
AWS_PROFILE=journal-dev ./scripts/setup/step-2b-create-backend-file.sh dev
AWS_PROFILE=journal-dev ./scripts/setup/step-3a-terraform-apply.sh dev
AWS_PROFILE=journal-dev ./scripts/setup/step-4a-deploy-web-to-s3.sh dev
```

Destroy:
```bash
AWS_PROFILE=journal-dev ./scripts/destroy/step-1a-terraform-destroy.sh dev
AWS_PROFILE=journal-dev ./scripts/destroy/step-1b-delete-terraform-backend.sh
```
