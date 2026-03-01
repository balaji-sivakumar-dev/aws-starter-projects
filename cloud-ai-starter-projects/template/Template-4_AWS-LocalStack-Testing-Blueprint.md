# Template 4: AWS LocalStack Testing Blueprint (Deferred)

Version: v0.1 (Planning Only)  
Date: March 1, 2026  
Purpose: Define a future template focused on local-first AWS testing via LocalStack, while preserving compatibility with real AWS deployment templates.

## 1) Goal
Template 4 will provide a repeatable local integration testing setup for the existing AWS serverless/container templates without changing their public API contracts.

## 2) Scope (Planned)
- LocalStack-backed infrastructure profile for Terraform.
- Local-first execution path for:
  - API Gateway + Lambda
  - DynamoDB
  - Step Functions
  - S3 static hosting
- Clear environment split:
  - `aws` (real cloud)
  - `localstack` (local integration)
- Test runbook and parity checklist.

## 3) Known Caveats (Captured for later implementation)
1. Cognito support is plan-gated in LocalStack and may have behavior differences vs AWS hosted flows.
2. Bedrock support is plan-gated and feature-limited in local emulation.
3. App Runner parity is uncertain for local testing compared with core serverless services.
4. Some services/features may require paid LocalStack tiers for full end-to-end parity.
5. LocalStack platform/auth requirements may change over time; setup docs must be kept current.

## 4) Out of Scope (for initial Template 4 draft)
- Full Bedrock fidelity.
- Full Cognito Hosted UI parity.
- Production deployment automation.
- Multi-account/multi-region enterprise bootstrap.

## 5) Proposed Architecture (High level)
- Keep existing Template 1/3 code contracts unchanged.
- Add provider/config toggle layer to Terraform for LocalStack endpoints.
- Add mode-specific env files and startup scripts.
- Add smoke tests that run identically against local and cloud where feasible.

## 6) Planned Deliverables (future)
- `template-4-aws-localstack-testing/` project skeleton.
- Terraform profiles and tfvars for `localstack`.
- LocalStack docker compose + bootstrap scripts.
- CLI-first setup guide.
- Compatibility matrix by service and feature.
- Manual TODO and known-gap tracker.

## 7) Acceptance Criteria (future)
- Local stack can be created/destroyed repeatedly.
- Core journal CRUD flow works locally end-to-end.
- Async AI enqueue path is testable with documented fallback behavior for unsupported AI services.
- Clear list of feature gaps vs AWS production.

## 8) Status
Deferred by design. Document created to capture direction and caveats; implementation will happen later.
