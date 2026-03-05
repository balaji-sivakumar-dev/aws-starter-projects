# API

Base path: API Gateway HTTP API default stage.

## Conventions
- Auth: Bearer JWT required for all routes except `GET /health`.
- Error shape: `{ "code": string, "message": string, "requestId": string }`.
- List pagination: `limit` + `nextToken`.

## Routes
- `GET /health`
- `GET /me`
- `GET /entries?limit=&nextToken=`
- `POST /entries`
- `GET /entries/{entryId}`
- `PUT /entries/{entryId}`
- `DELETE /entries/{entryId}` (soft delete)
- `POST /entries/{entryId}/ai` (enqueue workflow)

## Payloads
### Create Entry
Request:
```json
{ "title": "string", "body": "string" }
```

### Entry Response Item
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
