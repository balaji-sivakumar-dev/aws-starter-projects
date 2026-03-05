# Detailed Execution Plan - Template 1 AWS Journal

## Scope and Constraints
- Create a new reusable starter only under `cloud-ai-starter-projects/template-1-aws-journal/`.
- Keep `aws-sam-gateway-lambda-dynamodb/` read-only as a reference project.
- Implement only spec-defined capabilities for Template 1.
- Preserve strict separation:
  - Platform layer: auth, API edge, hosting, shared lambda module, observability baseline.
  - Domain layer: journal CRUD rules, entry schema, AI workflow behavior.

## Reuse vs New Build
### Reuse (reference-only patterns from existing SAM project)
- Lambda handler structure and simple routing baseline.
- DynamoDB helper style (lazy table/client initialization) adapted to single-table Journal model.
- Docs organization pattern for setup/architecture/runbook files.

### New implementation (Terraform + new architecture)
- Full Terraform module stack (`auth_cognito`, `api_gateway_http`, `lambda`, `dynamodb`, `step_functions`, `s3_spa_hosting`).
- New Journal domain APIs and single-table keys (`PK=USER#{userId}`, `SK=ENTRY#...`).
- Step Functions async workflow and AI Gateway Lambda with guardrails.
- React SPA with Cognito Hosted UI login and journal management UI.

## Iterative Build Plan Status
1. Bootstrap repository skeleton and placeholder docs. (completed)
2. Terraform platform base and module wiring. (completed)
3. API service and domain persistence. (completed)
4. Workflow + AI implementation (status transitions + Bedrock gateway). (completed)
5. React web app (login, list/detail/create/edit, AI trigger, aiStatus display). (completed)
6. Documentation and runbook finalization. (completed)
7. Detailed AWS account + Terraform setup guide (CLI-first). (completed)

## Validation Status (as of March 5, 2026)
- CRUD flow validated in AWS dev: login, create, list, view detail, update, delete.
- AI trigger workflow pending Bedrock model access enablement.

## Commit Cadence
- Commits were created after each valid iteration.
- Changes remain additive within `cloud-ai-starter-projects/template-1-aws-journal/`.
