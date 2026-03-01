# API

Base path: Cloud Function `api` HTTP endpoint.

## Conventions
- Auth: Firebase ID token bearer auth required for all routes except `GET /health`.
- User identity: `userId = Firebase UID`.
- Error shape: `{ "code": string, "message": string, "requestId": string }`.
- Pagination: `limit` and `nextToken`.

## Routes
- `GET /health`
- `GET /me`
- `GET /entries?limit=&nextToken=`
- `POST /entries`
- `GET /entries/{entryId}`
- `PUT /entries/{entryId}`
- `DELETE /entries/{entryId}` (soft delete)
- `POST /entries/{entryId}/ai` (enqueue async processor)

## Core payloads
Create request:
```json
{ "title": "string", "body": "string" }
```

Entry response item:
```json
{
  "entryId": "string",
  "userId": "firebase-uid",
  "title": "string",
  "body": "string",
  "createdAt": "ISO-8601",
  "updatedAt": "ISO-8601",
  "deletedAt": null,
  "aiStatus": "NOT_REQUESTED|QUEUED|PROCESSING|COMPLETE|FAILED",
  "summary": null,
  "tags": [],
  "aiUpdatedAt": null,
  "aiError": null
}
```
