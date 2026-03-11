# Architecture

## Layering

### Platform Layer (Reusable)
- `infra/terraform/modules/project_services`
- `infra/terraform/modules/iam`
- `infra/terraform/modules/observability`
- Firebase Hosting + Auth integration surface

Responsibilities:
- Enable required services
- Provision service accounts and IAM
- Establish baseline observability and deployment platform

### Domain Layer (Journal)
- `infra/terraform/modules/firestore`
- `infra/terraform/modules/workflow_primitives`
- `services/api/src/*`
- `services/workflows/src/*`

Responsibilities:
- Journal CRUD and per-user access rules
- Async AI processing and status transitions
- Firestore document model and soft delete behavior

## Request Flow
1. User logs in via Firebase Auth (email/password).
2. React app sends Firebase ID token to Cloud Functions API.
3. API verifies token and enforces `userId=uid` path ownership.
4. CRUD actions read/write `users/{userId}/entries/{entryId}`.
5. AI trigger enqueues async task (`ProcessEntryAIWorkflow` pattern).
6. Processor invokes AI Gateway (Vertex AI/Gemini) and updates derived fields.

## Stability Contract
- Route and error contracts mirror Template 1.
- Internal implementation can evolve while edge contract stays stable.
