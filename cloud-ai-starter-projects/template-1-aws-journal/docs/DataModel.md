# Data Model

## DynamoDB Single Table
- Table keys:
  - `PK` (string)
  - `SK` (string)
- Per-user partition:
  - `PK = USER#{userId}`

## Item Types
### Journal Entry Item
- `SK = ENTRY#{createdAt}#{entryId}`
- Attributes: `entryId`, `userId`, `title`, `body`, `createdAt`, `updatedAt`, `deletedAt`, `aiStatus`, `summary`, `tags`, `aiUpdatedAt`, `aiError`

### Entry Lookup Item
- `SK = ENTRYID#{entryId}`
- Attributes: `entrySk` pointer for direct entry lookup per user

## Isolation Rule
All entry reads/writes are done with `PK = USER#{jwt.sub}`. Cross-user access is not possible through API handlers.

## Soft Delete
`DELETE /entries/{entryId}` sets `deletedAt` and keeps item data in table.
