# Detailed Execution Plan - Template 3 Container + Serverless Journal

## Scope and Constraints
- Create all Template 3 assets under `cloud-ai-starter-projects/template-3-container-serverless-journal/`.
- Keep API/auth/response contracts stable across compute modes.
- Implement compute flexibility using Terraform module plug-ins.

## Delivery Plan
1. Bootstrap skeleton and docs placeholders. (completed)
2. Terraform shared platform and compute plug-in wiring. (completed)
3. Compute adapters: lambda and container with stable routes. (completed)
4. AI gateway/workflow adapters with guardrails. (completed)
5. Web app and contract validation notes. (completed)
6. Final docs: setup, migration, runbook, TODO. (completed)

## Post-implementation manual steps
1. Configure AWS profile and deploy target settings.
2. Build/push container image if using container/hybrid mode.
3. Apply Terraform for chosen mode.
4. Configure web app env and run smoke tests.
