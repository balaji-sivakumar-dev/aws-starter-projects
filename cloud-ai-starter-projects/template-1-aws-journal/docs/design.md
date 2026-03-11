# Design: Journal Summary Workflow (Bedrock)

Goal: add a weekly/monthly summary workflow that aggregates multiple journal entries into a single summary artifact.

## Scope
- Input: `userId`, `startDate`, `endDate` (ISO-8601)
- Output: summary text + optional tags + metadata (range, createdAt)
- Storage: new DynamoDB item type under the user partition

## API Contract
New route:
- `POST /summaries` with body:
```json
{
  "startDate": "2026-03-01",
  "endDate": "2026-03-07",
  "title": "Weekly Summary (optional)"
}
```
Response:
```json
{
  "summaryId": "uuid",
  "status": "QUEUED",
  "createdAt": "ISO-8601 UTC"
}
```

Optional read:
- `GET /summaries?startDate=&endDate=`

## Data Model
New item types in single table:
- Summary item:
  - `PK = USER#{userId}`
  - `SK = SUMMARY#{startDate}#{endDate}#{summaryId}`
  - Attributes: `summaryId`, `startDate`, `endDate`, `title`, `summary`, `tags`, `status`, `createdAt`, `updatedAt`, `error`

## Step Functions (ProcessSummaryWorkflow)
1. `ValidateRange` (Lambda) — validate dates and max range.
2. `FetchEntries` (Lambda) — query entries in range.
3. `ChunkEntries` (Lambda) — split into chunks if needed.
4. `MapSummaries` (Map state) — summarize each chunk via Bedrock.
5. `Aggregate` (Lambda) — combine chunk summaries into final summary.
6. `PersistSummary` (Lambda) — write to DynamoDB, set status `COMPLETE`.
7. `MarkFailed` (Catch) — set status `FAILED` with error.

## Bedrock Configuration
- Model: `amazon.nova-lite-v1:0` (current default)
- Limits: `MAX_INPUT_CHARS`, `MAX_OUTPUT_TOKENS`
- Rate limiting: reuse `AI_RATE_LIMIT_*`

## UI
- Add “Summarize Week/Month” action.
- Show summary status and output in profile or a new Summary panel.

## Open Questions
- Max range length (7/30/90 days?)
- Store summary as separate item vs embed in profile?
- Cost controls: enforce per-user daily summary limit?
