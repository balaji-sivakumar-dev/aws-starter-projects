# Template 1 Implementation & Testing Checklist

Use this checklist to track build + verification progress per environment.

## Implementation Checklist
- [x] Terraform modules and root stack wired.
- [x] Cognito Hosted UI configured.
- [x] API Gateway HTTP API with JWT authorizer.
- [x] Lambda CRUD handlers and routing.
- [x] DynamoDB single-table model.
- [x] Step Functions workflow + AI Gateway Lambda.
- [x] React SPA with login + CRUD UI.
- [x] Docs and CLI-first scripts.

## Environment Checklist (Dev Example)
- [x] AWS account configured with `AWS_PROFILE=journal-dev`.
- [x] Terraform backend bootstrapped.
- [x] Terraform apply completed.
- [x] App env exported from Terraform outputs.
- [x] Web app starts locally (`npm run dev`).

## Testing Checklist (Dev Example)
- [x] Login via Cognito Hosted UI.
- [x] Create entry.
- [x] List entries.
- [x] View entry detail.
- [x] Update entry.
- [x] Delete entry (soft delete).
- [ ] Trigger AI workflow (requires Bedrock model access).
- [ ] Confirm `aiStatus` transitions to `COMPLETE` or `FAILED`.
- [ ] Confirm `summary` + `tags` persisted.

## Notes
- Record test dates and environment details here if needed.
- If AI tests are blocked, confirm Bedrock access in the AWS account first.
