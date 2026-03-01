# Data Model

## Firestore Layout
- Collection path: `users/{userId}/entries/{entryId}`
- One user partition per UID

## JournalEntry fields
- `entryId`
- `userId`
- `title`
- `body`
- `createdAt`
- `updatedAt`
- `deletedAt` (soft delete marker)
- `aiStatus`
- `summary`
- `tags`
- `aiUpdatedAt`
- `aiError`

## Query model
- List query ordered by `createdAt` descending.
- List excludes soft deleted items (`deletedAt == null`).
- Pagination uses opaque `nextToken`.

## Isolation rule
All reads/writes use authenticated `userId` from verified Firebase token; cross-user access is blocked by path scoping.
