# API

Base path: Firebase Cloud Function `api` endpoint.

## Conventions
- Auth: Firebase ID token bearer auth required except `GET /health`.
- User identity: `userId = Firebase UID` from verified token.
- Error shape: `{ "code": string, "message": string, "requestId": string }`.
- Pagination: `limit` + opaque `nextToken`.

## Routes
- `GET /health`
- `GET /me`
- `GET /entries?limit=&nextToken=`
- `POST /entries`
- `GET /entries/{entryId}`
- `PUT /entries/{entryId}`
- `DELETE /entries/{entryId}` (soft delete)
- `POST /entries/{entryId}/ai` (enqueue async processing)

## Create payload
```json
{ "title": "string", "body": "string" }
```

## Entry payload
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
