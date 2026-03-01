# Template 2 TODO (Manual Setup + Validation)

## Environment Setup
- [ ] Create/select GCP project and enable billing.
- [ ] Authenticate CLI (`gcloud auth login`, `gcloud auth application-default login`).
- [ ] Link/select Firebase project (`firebase use <project_id>`).
- [ ] Enable required model access in Vertex AI/Gemini if needed.

## Terraform
- [ ] Copy `infra/terraform/environments/dev/dev.tfvars.example` to `dev.tfvars` and set values.
- [ ] Run `terraform init`.
- [ ] Run `terraform plan -var-file=environments/dev/dev.tfvars`.
- [ ] Run `terraform apply -var-file=environments/dev/dev.tfvars`.
- [ ] Capture outputs (`project_id`, `region`, `workflow_queue_name`).

## Firebase Functions/Hosting
- [ ] Set runtime config via CLI (`firebase functions:config:set ...`).
- [ ] Deploy functions (`firebase deploy --only functions`).
- [ ] Build web app (`npm --prefix apps/web install && npm --prefix apps/web run build`).
- [ ] Deploy hosting (`firebase deploy --only hosting`).

## Local Web App
- [ ] Copy `apps/web/.env.example` to `apps/web/.env`.
- [ ] Fill `VITE_FIREBASE_*` and `VITE_API_BASE_URL`.
- [ ] Run `npm --prefix apps/web run dev` and confirm app loads.

## Smoke Tests
- [ ] `GET /health` returns 200.
- [ ] Login/register works.
- [ ] `/me` returns current user.
- [ ] Create/list/get/update/delete entry works.
- [ ] `POST /entries/{entryId}/ai` enqueues processing.
- [ ] Entry moves through `aiStatus` states and persists summary/tags.
