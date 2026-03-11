# Setup

Primary guide:
- `docs/GCP-Firebase-Terraform-Setup.md` (CLI-first)

## Completion vs Manual Work
- Code/template implementation: complete.
- Manual cloud setup/deploy/test: required before declaring environment ready.

## Quick Start
1. Configure GCP/Firebase and auth via CLI.
2. Run Terraform apply for foundation.
3. Deploy functions and hosting with Firebase CLI.
4. Configure `apps/web/.env` and run the web app.
5. Execute smoke checks from `docs/Runbook.md`.

## UI-only minimum
- GCP billing/account bootstrap
- Firebase project linking (only if CLI path is blocked)
- Model access enablement if org policy requires console action

## TODO Tracker
- See `docs/TODO.md` for remaining manual setup and validation tasks.
