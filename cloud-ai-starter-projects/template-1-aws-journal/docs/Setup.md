# Setup

Primary guide:
- `docs/AWSAccount-Terraform-Setup.md` (CLI-first)

## Quick Start
1. Complete AWS/bootstrap steps in `AWSAccount-Terraform-Setup.md`.
2. Deploy infra with Terraform (`plan/apply`).
3. Copy Terraform outputs into `apps/web/.env`.
4. Run web app locally and execute smoke checks from `docs/Runbook.md`.

## Notes
- Prefer CLI for all operations except required AWS Console actions:
  - AWS account signup/root security setup
  - Bedrock model access enablement
