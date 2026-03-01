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
- Lambda handler structure and in-function routing style as baseline simplicity reference.
- DynamoDB helper structure (`table()` style initialization) adapted for new domain needs.
- Basic docs structure pattern (`Setup`, architecture-oriented markdown docs).

### New implementation (Terraform + new architecture)
- Full Terraform module stack (`auth_cognito`, `api_gateway_http`, `lambda`, `dynamodb`, `step_functions`, `s3_spa_hosting`).
- New Journal domain APIs and single-table keys (`PK=USER#{userId}`, `SK=ENTRY#...`).
- Step Functions async workflow and AI Gateway Lambda with guardrails.
- React SPA with Cognito Hosted UI login and journal management UI.

## Iterative Build Plan
1. Bootstrap repository skeleton and placeholder docs. (current step)
2. Terraform platform base:
   - variables, naming, providers, backend placeholders
   - S3 SPA hosting + Cognito + DynamoDB modules
3. Terraform integration:
   - Lambda packaging wiring, API routes/JWT authorizer, Step Functions
   - root outputs (`api_base_url`, `cognito_domain`, `cognito_client_id`, `region`, `web_bucket_name`, `site_url`)
4. API service:
   - /health, /me, /entries CRUD, /entries/{entryId}/ai enqueue
   - requestId propagation and error contract `{ code, message, requestId }`
5. Workflow + AI:
   - state machine Validate -> AI Gateway -> Persist -> COMPLETE/FAILED
   - retries for transient failures and status updates
6. React web app:
   - Hosted UI login/logout
   - list/detail/create/edit, AI trigger button, aiStatus + summary/tags rendering
7. Documentation + runbook completion and smoke-test checklist.

## Commit Cadence
- Commit after each valid iteration above with clear scoped messages.
- Keep commits additive in the new template folder only.

## Iteration Status
- Iteration 1 complete: project skeleton + docs placeholders committed.
- Iteration 2 in progress: Terraform platform modules and root wiring for dev are being implemented.
