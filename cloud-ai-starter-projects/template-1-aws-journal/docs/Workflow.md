# Workflow

Current state machine file:
- `services/workflows/statemachine/process_entry_ai.asl.json`

Current flow (Iteration 3 prep):
- ValidateInput
- InvokeAIGateway (with retry/catch)
- MarkComplete / MarkFailed

Next iteration will align fully with spec transitions:
- Validate -> mark PROCESSING -> AI Gateway -> persist summary/tags -> COMPLETE
- Failure path updates `aiStatus=FAILED` + `aiError`
