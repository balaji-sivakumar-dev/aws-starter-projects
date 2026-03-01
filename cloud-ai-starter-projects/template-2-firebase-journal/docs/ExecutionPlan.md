# Detailed Execution Plan - Template 2 Firebase Journal

## Scope and Constraints
- Create everything under `cloud-ai-starter-projects/template-2-firebase-journal/`.
- Keep Template 1 and other existing projects as read-only references.
- Match Template 2 spec with no extra features.
- Keep strict platform/domain separation.

## Reuse vs New Build
### Reuse (from Template 1 patterns)
- Stable route contract and consistent error shape.
- Journal domain fields and soft delete semantics.
- Iterative delivery cadence with scoped commits.

### New implementation (Firebase/GCP)
- Terraform for project services, IAM, Firestore, and async workflow primitives.
- Firebase Auth token verification in backend.
- Firestore per-user entry layout and pagination tokens.
- Internal AI Gateway for Vertex AI/Gemini calls only.
- Firebase CLI deployment split for Hosting + Functions.

## Iterative Build Plan
1. Bootstrap skeleton and placeholders. (completed)
2. Terraform foundation modules and root wiring. (completed)
3. Cloud Functions API routes and Firestore data access. (completed)
4. Async workflow + AI Gateway with guardrails and status updates. (completed)
5. React web app with Firebase Auth and journal UI. (completed)
6. Docs finalization with CLI-first setup/runbook and smoke checklist. (completed)

## Commit Cadence
- Commits created after each valid iteration.
- Changes kept additive in Template 2 folder only.
