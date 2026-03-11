# Specs

## API
Base path: API Gateway HTTP API default stage.

Conventions:
- Auth: Bearer JWT required for all routes except `GET /health`.
- Error shape: `{ "code": string, "message": string, "requestId": string }`.
- List pagination: `limit` + `nextToken`.

Routes:
- `GET /health`
- `GET /me`
- `GET /entries?limit=&nextToken=`
- `POST /entries`
- `GET /entries/{entryId}`
- `PUT /entries/{entryId}`
- `DELETE /entries/{entryId}` (soft delete)
- `POST /entries/{entryId}/ai` (enqueue workflow)

Create Entry request:
```json
{ "title": "string", "body": "string" }
```

Entry response item:
```json
{
  "entryId": "uuid",
  "userId": "cognito-sub",
  "title": "string",
  "body": "string",
  "createdAt": "ISO-8601 UTC",
  "updatedAt": "ISO-8601 UTC",
  "deletedAt": null,
  "aiStatus": "NOT_REQUESTED|QUEUED|PROCESSING|COMPLETE|FAILED",
  "summary": null,
  "tags": [],
  "aiUpdatedAt": null,
  "aiError": null
}
```

## Data Model
DynamoDB single table:
- Keys: `PK` (string), `SK` (string)
- Per-user partition: `PK = USER#{userId}`

Item types:
- Journal entry item: `SK = ENTRY#{createdAt}#{entryId}`
- Entry lookup item: `SK = ENTRYID#{entryId}` with `entrySk` pointer

Isolation rule:
- Reads and writes are always scoped to `PK = USER#{jwt.sub}`.

Soft delete:
- `DELETE /entries/{entryId}` sets `deletedAt` and preserves item data.

## AI Workflow
State machine file:
- `services/workflows/statemachine/process_entry_ai.asl.json`

ProcessEntryAIWorkflow steps:
1. `ValidateInput`
2. `InvokeAIGateway`
3. `PersistDerivedFields` (AI Gateway writes to DynamoDB)
4. `MarkComplete`

Failure path:
- Any error routes to `MarkFailed`.
- AI Gateway updates `aiStatus=FAILED` and `aiError` before failing the state machine.

AI Gateway Lambda responsibilities:
- Enforce limits: `MAX_INPUT_CHARS`, `MAX_OUTPUT_TOKENS`, rate limits.
- Load entry via per-user keys.
- Set `aiStatus=PROCESSING`.
- Call Bedrock model configured by `BEDROCK_MODEL_ID`.
- Persist `summary`, `tags`, `aiUpdatedAt`, `aiStatus=COMPLETE`.
- On error, persist `aiStatus=FAILED` and `aiError`.
