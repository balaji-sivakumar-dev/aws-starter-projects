# Template 1 - AWS Serverless Journal Starter Kit (Terraform)

This project is a new reusable template for Template 1.

Status: Template 1 implementation complete, including CLI-first setup guides and helper scripts.

Docs index:
- `docs/AWSAccount-Terraform-Setup.md` — CLI-first AWS + Terraform setup
- `docs/Setup.md` — quick start
- `docs/Runbook.md` — smoke tests and validation order
- `docs/Template1-AWS-Setup-Checklist.md` — cost/safety checklist
- `docs/Architecture.md` — platform/domain layout
- `docs/API.md` — route contract
- `docs/DataModel.md` — DynamoDB single-table model
- `docs/Workflow.md` — AI workflow behavior
- `docs/ExecutionPlan.md` — implementation plan summary
- `docs/archived/review_comments.md` — archived review notes

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
