# Runbook

## Manual Testing Readiness
- Backend and workflow tests: ready after Terraform apply + functions deploy.
- Full end-to-end UI tests: ready after web `.env` config and local run.

## Setup Order (CLI-first)
1. Follow `docs/GCP-Firebase-Terraform-Setup.md`.
2. Apply Terraform foundation.
3. Deploy Firebase Functions.
4. Configure and run web app.
5. Run smoke checks.

## Smoke Checklist
1. `GET /health` returns 200.
2. Register/login from web app via Firebase Auth.
3. Confirm `/me` loads user info.
4. Create entry and confirm list/detail.
5. Update entry and verify persistence.
6. Delete entry and verify it disappears from list.
7. Trigger AI and observe `aiStatus` moves QUEUED -> PROCESSING -> COMPLETE/FAILED.
8. Confirm `summary` and `tags` populate on success.

## Troubleshooting
- `UNAUTHORIZED`: verify Firebase ID token is sent in `Authorization` header.
- Queue enqueue failures: verify `app.queue_name`, `app.queue_location`, and IAM role `roles/cloudtasks.enqueuer`.
- AI failures: verify Vertex API enabled, model availability, and `VERTEX_AI_MODEL` config.
