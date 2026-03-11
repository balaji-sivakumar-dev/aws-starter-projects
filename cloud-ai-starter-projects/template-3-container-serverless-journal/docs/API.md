# API

Template 3 keeps the same stable API contract as Templates 1 and 2.

## Conventions
- Auth: JWT bearer required for all routes except `GET /health`.
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
- `POST /entries/{entryId}/ai` (enqueue workflow)

## Stability rule
Compute mode (`serverless`, `container`, `hybrid`) must not change route names, auth expectation, or response shape.
