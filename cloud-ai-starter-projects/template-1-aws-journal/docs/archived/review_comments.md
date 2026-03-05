# Code Review: cloud-ai-starter-projects (Template 1)

**Date:** March 01, 2026  
**Context:** Review of `template-1-aws-journal` against the `Template-1_AWS-Serverless-Journal-StarterKit_Terraform` specification.

## Overview
The current branch (`template_aws`) contains a full end-to-end implementation of the AWS Serverless Journal Starter Kit. The changes encompass Terraform infrastructure modules, backend Python services (API and AI Workflows), and a React SPA.

Overall, the codebase successfully strictly follows the boundaries set by the Template 1 specification. The edge contract is intact, while the compute side separates standard CRUD from asynchronous operations gracefully.

---

## Step-by-Step Code Review Comments

### 1. Infrastructure & Terraform
- **Status:** **PASS**
- **Comments:**
  - The architectural layers (Platform Layer vs. Domain Layer) are correctly separated. 
  - Modules such as `auth_cognito`, `api_gateway_http`, `dynamodb`, and `step_functions` abstract AWS specifics efficiently.
  - The API Gateway connects to Cognito JWT authorizers as expected. 
- **Recommendation:**
  - In `infra/terraform/main.tf` line `115`, the `BedrockInvoke` IAM role allows `resources = ["*"]`. Consider tightening this policy to only allow execution of the specific foundational model ID provided in `var.bedrock_model_id` to adhere strictly to the principle of least privilege.

### 2. Backend API Services
- **Status:** **PASS**
- **Comments:**
  - `services/api/src/handlers.py` implements all endpoints (`/health`, `/me`, `/entries`, `/entries/{entryId}/ai`) according to the REST contract.
  - The claims validation extracts `userId` from the JWT `sub` exactly as specified. 
  - The DynamoDB Single-Table Design correctly leverages Partition Key spacing (`PK=USER#{userId}`) and Sort Keys, and successfully treats deletions as soft deletes (via `deletedAt`).

### 3. Asynchronous AI Workflow
- **Status:** **PASS**
- **Comments:**
  - `services/workflows/statemachine/process_entry_ai.asl.json` validates input safely prior to invoking the `ai_gateway`.
  - Bedrock interaction in `services/workflows/src/ai_gateway.py` integrates with the configured rate limit variables correctly (e.g., verifying limits against DynamoDB keys `SK=AIRATE#{window_bucket}`).
  - Output token guards (`max_output_tokens=256`) and input size truncation safeguard against heavy generative AI billing.
- **Recommendation:**
  - Verify that the rate limit DynamoDB lock doesn't encounter excessive contention under high parallel usage, although the `ADD requestCount :inc` logic is an optimal non-locking solution. 

### 4. React Frontend (SPA)
- **Status:** **PASS**
- **Comments:**
  - `App.jsx` cleanly boots up standard authentication procedures via the Cognito Hosted UI context logic mapping. 
  - The API wrapper at `api/client.js` accurately manages injecting the `Authorization: Bearer <token>` on all outbound domain requests.
  - Usage of `useJournalApp` state orchestrates rendering states efficiently handling list generation, creation, updating, and UI loading indicators organically.
- **Recommendation:**
  - No direct fixes needed. As an enhancement, consider implementing debounced polling or WebSockets to proactively listen to AI Task completion statuses instead of relying entirely on manual front-end refresh actions.

## Actionable Fixes Summary
1. **[Minor] Security / IAM Policy:** Restrict Bedrock access scope in `main.tf` module `lambda_ai` to target specific models instead of all resources `["*"]`.
2. **[Minor] CI/CD Verification:** Ensure `.env` configurations are correctly securely packaged in future automation pipelines since Vite requires `VITE_` variables accessible pre-build.

---
*Review complete. The code is well-structured and maps effectively to the targeted starter-kit boundaries.*
