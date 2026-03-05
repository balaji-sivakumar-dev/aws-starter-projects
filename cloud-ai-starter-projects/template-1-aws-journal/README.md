# Template 1 - AWS Serverless Journal Starter Kit (Terraform)

This project is a new reusable template for Template 1.

Status: Template 1 implementation complete, including CLI-first setup guides and helper scripts.

See:
- `docs/ExecutionPlan.md`
- `docs/AWSAccount-Terraform-Setup.md`
- `docs/Runbook.md`

## Scripts (CLI-first)
Run from repo root:
```bash
AWS_PROFILE=journal-dev ./scripts/setup/step-1-aws-configure.md
AWS_PROFILE=journal-dev ./scripts/setup/step-2-bootstrap-terraform-backend.sh
AWS_PROFILE=journal-dev ./scripts/setup/step-2b-create-backend-file.sh dev
AWS_PROFILE=journal-dev ./scripts/setup/step-3a-terraform-apply.sh dev
AWS_PROFILE=journal-dev ./scripts/setup/step-4a-export-outputs-to-env.sh dev
```

Destroy:
```bash
AWS_PROFILE=journal-dev ./scripts/destroy/step-1a-terraform-destroy.sh dev
AWS_PROFILE=journal-dev ./scripts/destroy/step-1b-delete-terraform-backend.sh
```
