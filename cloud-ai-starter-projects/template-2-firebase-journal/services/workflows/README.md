# Workflows Service

Async processing components for Template 2 AI flow.

## Components
- `src/processor.js`: queue/HTTP processor that updates `aiStatus` transitions.
- `src/ai_gateway.js`: only module allowed to call Vertex AI/Gemini.

## Processing flow
1. Validate request payload (`userId`, `entryId`, `requestId`).
2. Rate limit check (per-user, rolling window bucket).
3. Load Firestore entry and set `aiStatus=PROCESSING`.
4. Generate summary/tags via Vertex AI/Gemini.
5. Persist derived fields and mark `aiStatus=COMPLETE`.
6. On error, mark `aiStatus=FAILED` and persist `aiError`.
