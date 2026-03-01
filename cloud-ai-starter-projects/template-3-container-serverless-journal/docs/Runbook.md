# Runbook

## Manual Testing Readiness
- Backend workflow test: ready after Terraform apply.
- Full end-to-end UI test: ready after web `.env` setup.

## Smoke checklist
1. `GET /health` returns 200.
2. Login via Cognito Hosted UI.
3. `GET /me` returns authenticated user.
4. Create/list/get/update/delete entry works.
5. Trigger AI and verify status transitions to COMPLETE or FAILED.
6. Confirm summary/tags and aiError behavior.

## Mode-specific checks
- `serverless`: ensure API integrates with lambda function.
- `container`: ensure App Runner URL is reachable and JWT verification works in container.
- `hybrid`: ensure both compute adapters are reachable via same edge contract.
