# Runbook

## Manual Testing Readiness
- Backend + workflow test: ready after Terraform apply.
- Full end-to-end manual test (including UI): ready now.

## Setup Order
1. Follow `docs/AWSAccount-Terraform-Setup.md`.
2. Deploy Terraform.
3. Configure `apps/web/.env` from Terraform outputs.
4. Start web app and run smoke checks.

## Smoke Checklist
1. `GET /health` returns 200.
2. Open web app and login via Cognito Hosted UI.
3. Confirm profile data loads from `GET /me`.
4. Create entry and verify it appears in list/detail.
5. Edit entry and verify updates persist.
6. Trigger AI (`POST /entries/{entryId}/ai`).
7. Refresh detail until `aiStatus` is `COMPLETE` or `FAILED`.
8. Validate `summary` and `tags` appear when complete.
