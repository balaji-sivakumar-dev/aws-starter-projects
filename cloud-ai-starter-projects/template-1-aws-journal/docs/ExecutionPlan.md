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

## Iterative Build Plan
1. Bootstrap repository skeleton and placeholder docs. (complete)
2. Terraform platform base and module wiring. (complete)
3. API service and domain persistence:
   - /health, /me, /entries CRUD, /entries/{entryId}/ai enqueue
   - requestId propagation and error contract `{ code, message, requestId }`
   - per-user isolation with `PK=USER#{sub}`
4. Workflow + AI full implementation:
   - status transitions (QUEUED/PROCESSING/COMPLETE/FAILED)
   - AI Gateway guardrails + Bedrock call + derived fields persistence
5. React web app:
   - Hosted UI login/logout
   - list/detail/create/edit, AI trigger button, aiStatus + summary/tags rendering
6. Documentation + runbook completion and smoke-test checklist.

## Commit Cadence
- Commit after each valid iteration above with clear scoped messages.
- Keep commits additive in the new template folder only.
