# Architecture

## Design principle
Keep API edge/auth/domain stable while swapping compute adapters.

## Shared platform modules
- `auth` (Cognito)
- `api_edge` (API Gateway HTTP API + JWT authorizer)
- `db` (DynamoDB single-table)
- `workflow` (Step Functions)
- `web_hosting` (S3 static hosting)

## Compute plug-ins
- `compute_lambda` for serverless runtime
- `compute_container` for App Runner runtime
- `ai_gateway` as separate runtime boundary

## Deployment modes
- `serverless`: API routes -> Lambda adapter
- `container`: API routes -> App Runner adapter
- `hybrid`: lambda handles CRUD routes, container handles `POST /entries/{entryId}/ai`

## Data model
- `PK=USER#{userId}`
- `SK=ENTRY#{createdAt}#{entryId}`
- lookup item `SK=ENTRYID#{entryId}`
