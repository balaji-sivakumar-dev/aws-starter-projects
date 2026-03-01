# Workflow

State machine file:
- `services/workflows/statemachine/process_entry_ai.asl.json`

## ProcessEntryAIWorkflow
1. `ValidateInput`
2. `InvokeAIGateway` (retry on transient Lambda errors)
3. `PersistDerivedFields` (pass-through marker; AI Gateway writes to DynamoDB)
4. `MarkComplete`

Failure path:
- Any error routes to `MarkFailed`.
- AI Gateway updates entry `aiStatus=FAILED` and `aiError` before failing the state machine.

## AI Gateway Lambda Responsibilities
- Enforces hard limits:
  - `MAX_INPUT_CHARS`
  - `MAX_OUTPUT_TOKENS`
  - per-user rate limit hook (`AI_RATE_LIMIT_MAX_REQUESTS` + `AI_RATE_LIMIT_WINDOW_SECONDS`)
- Loads entry via per-user keys.
- Sets `aiStatus=PROCESSING`.
- Calls Bedrock model configured by `BEDROCK_MODEL_ID`.
- Persists `summary`, `tags`, `aiUpdatedAt`, and `aiStatus=COMPLETE`.
- On error, persists `aiStatus=FAILED` and `aiError`.
