# API Service (Cloud Functions)

Implements Template 2 route contract parity with Template 1:
- GET /health
- GET /me
- GET /entries
- POST /entries
- GET /entries/{entryId}
- PUT /entries/{entryId}
- DELETE /entries/{entryId}
- POST /entries/{entryId}/ai

## Auth
- Verifies Firebase ID token from `Authorization: Bearer <token>`
- Uses `uid` as `userId`

## Data model
- Firestore path: `users/{userId}/entries/{entryId}`
- Soft delete via `deletedAt`
