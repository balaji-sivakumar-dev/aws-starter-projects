# Runbook

## Readiness by Iteration
- Current: infra + API + workflow code is implemented.
- Pending: React web app and full end-to-end smoke walkthrough.

## When You Can Manually Test
- You can manually test API + workflow after:
  1. AWS account is ready
  2. Terraform apply succeeds
  3. Cognito test user exists
- Full end-to-end UI testing starts after web app iteration is completed.

## When to Set Up AWS Accounts
Set up AWS account access now (before next deploy test cycle), including:
- IAM credentials/profile with permission for Cognito, API Gateway v2, Lambda, DynamoDB, Step Functions, S3, CloudWatch, Bedrock.
- Bedrock model access enabled for the chosen model in target region.

## Basic Smoke Checklist (post-apply)
1. `GET /health` returns 200.
2. Login via Cognito Hosted UI and call `GET /me` with token.
3. Create an entry via `POST /entries`.
4. List entries via `GET /entries`.
5. Trigger AI via `POST /entries/{entryId}/ai`.
6. Poll `GET /entries/{entryId}` until `aiStatus` becomes `COMPLETE` or `FAILED`.
