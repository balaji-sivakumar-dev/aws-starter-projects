# Workflow

## Async Pattern
Template 2 uses Cloud Tasks as the workflow primitive in v1.

- Queue: `${app_prefix}-${env}-process-entry-ai`
- Enqueue path: `POST /entries/{entryId}/ai`
- Processor payload: `{ userId, entryId, requestId }`

## Processing contract
1. Validate payload and ownership context.
2. Set `aiStatus=PROCESSING`.
3. Invoke internal AI Gateway (`services/workflows/src/ai_gateway.js`).
4. Persist `summary`, `tags`, `aiUpdatedAt`, `aiStatus=COMPLETE`.
5. On failure, set `aiStatus=FAILED` and `aiError`.

## Guardrails
- `AI_MAX_INPUT_CHARS`
- `AI_MAX_OUTPUT_TOKENS`
- `AI_RATE_LIMIT_MAX_REQUESTS`
- `AI_RATE_LIMIT_WINDOW_SECONDS`

## Deployment note
In this template, workflow processor code is isolated under `services/workflows` so teams can deploy it as a dedicated function/service while keeping API edge stable.
