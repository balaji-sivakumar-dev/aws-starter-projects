# Runbook

## Manual Testing Readiness
- Backend + workflow test: ready after Terraform apply.
- Full end-to-end manual test (including UI): ready now once web `.env` is configured.

## When to Set Up AWS Accounts
Set up AWS account access now (if not already done), including:
- IAM credentials/profile with required service access.
- Bedrock model access enabled in your chosen region.

## Smoke Checklist
1. `GET /health` returns 200.
2. Open web app and login via Cognito Hosted UI.
3. Confirm profile data loads from `GET /me`.
4. Create entry and verify it appears in list/detail.
5. Edit entry and verify updates persist.
6. Trigger AI (`POST /entries/{entryId}/ai`).
7. Refresh detail until `aiStatus` is `COMPLETE` or `FAILED`.
8. Validate `summary` and `tags` appear when complete.
