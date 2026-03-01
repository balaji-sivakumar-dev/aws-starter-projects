# Architecture

## Layering

### Platform Layer (Reusable)
- `infra/terraform/modules/auth_cognito`
- `infra/terraform/modules/api_gateway_http`
- `infra/terraform/modules/lambda`
- `infra/terraform/modules/s3_spa_hosting`

Responsibilities:
- Auth boundary (Cognito Hosted UI + JWT)
- Stable HTTP API edge and route contract
- Generic Lambda packaging/runtime/roles
- Static SPA hosting

### Domain Layer (Journal)
- `infra/terraform/modules/dynamodb`
- `infra/terraform/modules/step_functions`
- `services/api/src/*`
- `services/workflows/src/*`

Responsibilities:
- Journal entry CRUD and per-user data isolation
- Single-table key model (`PK=USER#{userId}`)
- AI workflow and derived field persistence (`summary`, `tags`, `aiStatus`)

## Request Flow
1. User logs in via Cognito Hosted UI.
2. Web app sends bearer JWT to API Gateway HTTP API.
3. JWT authorizer validates issuer/audience.
4. API Lambda performs journal CRUD in DynamoDB.
5. `POST /entries/{entryId}/ai` starts Step Functions execution.
6. AI Gateway Lambda calls Bedrock and persists derived fields.

## Stability Contract
- Stable edge: routes, auth mechanism, error shape.
- Swappable internals: lambda/workflow implementation can evolve behind the same API contract.
