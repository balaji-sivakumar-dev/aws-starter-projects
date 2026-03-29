# Lessons Learned from Template 3 (Reflect)

> Extracted from 23 fix commits, 112 test cases, and the full build history.
> These become **binding rules** for the base template and all future projects.

---

## Part 1: What Broke and Why

### 1. Routes Coded but Never Registered (3 separate incidents)

**What happened:** Insights routes, admin routes, and RAG routes were all implemented
in Lambda handler code but never added to the Terraform `api_routes` map. API Gateway
returned 404 for every one of them. Each time it was discovered only after deploying
and manually testing.

**Root cause:** Routes are defined in **two unconnected places** — Python handler code
and Terraform HCL locals block. No validation that they match.

**Cost:** 3 fix commits, each requiring a `make deploy-backend` cycle (~5 minutes).

---

### 2. CORS Broken on Every New Header (4 incidents)

**What happened:**
- First deploy: zero CORS config → every browser API call blocked.
- Second fix: used `https://*.cloudfront.net` wildcard → API Gateway v2 rejects
  glob patterns (only exact origins or literal `*`).
- Third fix: added `X-LLM-Provider` custom header to frontend but not to
  `allow_headers` → header silently dropped on cross-origin requests.
- Fourth: `X-User-Id` header added for local dev but not in CORS → same issue.

**Root cause:** CORS was added reactively. No standard header allowlist.

---

### 3. Bedrock Region / Model Parameters Wrong (3 incidents)

**What happened:**
- Titan Embeddings V2 configured with `dimensions=1536` (that's V1). V2 only supports
  256/512/1024 → every embedding call failed with `ValidationException`.
- Lambda in `ca-central-1`, Bedrock models not available there → `boto3.client("bedrock-runtime")`
  defaulted to Lambda's region → "model not available".
- Fixed `BEDROCK_REGION` in `embeddings.py` but forgot to apply same fix in
  `ai_gateway.py` → LLM calls still broken.

**Root cause:** Model parameters from memory, not validated. Fix applied to one file
but not grepped across codebase.

---

### 4. SSM Values Stored but Never Read by Deploy Scripts (2 incidents)

**What happened:**
- `admin_emails` stored in SSM by `step-2b` script but `step-3c` never read it back.
  Terraform received empty string → Lambda `ADMIN_EMAILS` env var was always empty →
  admin tab never appeared.
- Same pattern with `allowed_emails` — script stored it, but the variable name in
  the read-back script had a typo.

**Root cause:** Store and read are in different scripts with no validation that the
round-trip works.

---

### 5. Auth Route Ordering in Lambda Handler (1 incident)

**What happened:** `/config/providers` endpoint was placed **after** the `get_user_id()`
auth gate in the Lambda handler. Even though API Gateway had `authorization=NONE` on
the route, the Lambda handler itself rejected unauthenticated requests. Had to move
the route handler above the auth check.

**Root cause:** Two auth layers (API Gateway JWT + Lambda handler) with different
route-level configs. Unauthenticated routes must be handled before the auth middleware
in **both** layers.

---

### 6. Terraform HCL Syntax Gotchas (5 incidents)

- Multi-line ternary without parentheses → Terraform treated newline as end of expression.
- BSD `sed` on macOS doesn't support `\s` → shell scripts failed to parse `.tfvars`.
- S3 bucket with public policy → AWS account had Block Public Access enabled at account
  level → silent 403s. Had to switch to CloudFront OAC.
- Cognito domain prefix as manual placeholder → required two commits to auto-generate.
- Duplicate `data "aws_region"` in two files within same module → Terraform error.

---

### 7. DynamoDB Consistency After Writes (1 incident)

**What happened:** `list_entries` used eventually consistent reads. After creating an
entry, the immediate list response sometimes didn't include the new entry.

**Root cause:** DynamoDB Query defaults to eventually consistent reads. Need
`ConsistentRead=True` for any read-after-write path.

---

### 8. API Contract Field Name Mismatches (2 incidents)

- Backend returned `embeddedCount`, frontend expected `totalVectors`.
- Container API used `if_not_exists()` in UpdateExpression (sets only if attribute
  doesn't exist) instead of plain `SET` (always overwrites). Updates silently did nothing.

**Root cause:** No shared contract spec. Field names defined implicitly in handler code.

---

### 9. Docker / Local Dev Issues (1 incident)

- DynamoDB Local with SQLite: container runs as non-root, Docker volume owned by root →
  `SQLITE_CANTOPEN`. Fixed by using `-inMemory` mode.
- Port open ≠ service ready. boto3 connected before DynamoDB was accepting queries.

---

### 10. Lambda Had No Logging (1 incident, multi-hour debugging)

**What happened:** DynamoDB `TransactWriteItems` failed with permission errors, but
Lambda had no `logging.getLogger()` configured. CloudWatch showed zero output. Took 5
fix commits across several hours to debug blind.

---

## Part 2: Guiding Principles for the Base Template

These are non-negotiable rules. Every principle has a corresponding "what broke" above.

---

### Principle 1: Single Source of Truth for Routes

```
routes.yaml (or OpenAPI spec)
  ↓ generates →  Terraform api_routes map
  ↓ generates →  Lambda handler dispatch table
  ↓ validates →  FastAPI route decorators (at test time)
```

**Rule:** If a route exists in handler code, it MUST exist in the infrastructure route
map. Validate this in CI with a simple script that diffs the two lists.

**Minimum implementation:** A `routes.yaml` file at project root:
```yaml
routes:
  - path: /health
    method: GET
    auth: none
  - path: /me
    method: GET
    auth: jwt
  - path: /entries
    method: GET
    auth: jwt
  - path: /entries
    method: POST
    auth: jwt
```

The Terraform `main.tf` locals block and the Lambda handler dispatch both read from
this definition. A `make validate-routes` target checks alignment.

---

### Principle 2: CORS is Day-Zero Infrastructure

**Rule:** The API Gateway module ships with this CORS config from the first commit:
```hcl
cors_configuration {
  allow_origins = ["*"]
  allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
  allow_headers = [
    "Content-Type",
    "Authorization",
    "X-User-Id",
    "X-Request-Id",
    "X-LLM-Provider"
  ]
  max_age = 300
}
```

**Rule:** The header allowlist lives in a shared constant (or `routes.yaml`). When
adding a custom header anywhere in the codebase, a CI check fails if it's not in the
CORS allowlist.

**Rule:** Never use wildcard patterns in `allow_origins` for API Gateway v2. Only
exact URLs or literal `*`.

---

### Principle 3: Structured Logging from Line One

**Rule:** Every Lambda handler starts with:
```python
import logging
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
```

**Rule:** Every handler entry point logs: method, path, user_id, request_id.
Every error path logs: error code, message, traceback.

**Rule:** The base template includes a `logging_config.py` that configures JSON
structured logging for both FastAPI and Lambda.

---

### Principle 4: Validate External Service Parameters at Deploy Time

**Rule:** Bedrock model IDs, dimensions, and region availability are validated in a
`make validate-config` target that:
1. Reads `BEDROCK_REGION`, `BEDROCK_MODEL_ID`, `EMBEDDING_DIMENSIONS` from config.
2. Calls `bedrock.list_foundation_models()` to verify the model exists in that region.
3. Fails fast with a clear error message before any Terraform runs.

**Rule:** All Bedrock/external API calls use an explicit `region_name` parameter from
env var. Never default to `AWS_REGION`.

**Rule:** When fixing a pattern in one file, grep the entire codebase for the same
pattern: `grep -r "bedrock-runtime" --include="*.py"` and fix all occurrences.

---

### Principle 5: SSM Round-Trip Validation

**Rule:** The `store-secrets.sh` script writes values. The `deploy-backend.sh` script
reads them back. Both scripts use the same SSM path constants from a shared
`scripts/config.sh` source file:
```bash
# scripts/config.sh — single source of truth for SSM paths
SSM_PREFIX="/${APP_PREFIX}/${ENV}"
SSM_ALLOWED_EMAILS="${SSM_PREFIX}/cognito/allowed_emails"
SSM_ADMIN_EMAILS="${SSM_PREFIX}/cognito/admin_emails"
SSM_GROQ_KEY="${SSM_PREFIX}/ai/groq_api_key"
```

**Rule:** `make deploy-backend` includes a pre-flight check that reads all required
SSM parameters and fails with a clear message if any are missing.

---

### Principle 6: Unauthenticated Routes Are Explicit and First

**Rule:** The Lambda handler dispatch has two phases:
```python
# Phase 1: Unauthenticated routes (before auth check)
OPEN_ROUTES = {
    ("GET", "/health"): handle_health,
    ("GET", "/config/providers"): handle_config,
}

# Phase 2: Auth check
user_id = get_user_id(event)  # raises 401 if invalid

# Phase 3: Authenticated routes
AUTH_ROUTES = {
    ("GET", "/entries"): handle_list_entries,
    ...
}
```

**Rule:** Every route in `routes.yaml` has an explicit `auth: none | jwt` field.
The Lambda handler and API Gateway route both respect this field.

---

### Principle 7: Consistent Response Envelope

**Rule:** Every endpoint returns the same envelope, regardless of adapter (FastAPI or Lambda):
```json
{
  "data": { ... },          // or "items": [...] for lists
  "meta": {
    "requestId": "uuid",
    "nextToken": "token"    // only for paginated lists
  }
}
```

**Rule:** Every error returns:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message"
  },
  "meta": {
    "requestId": "uuid"
  }
}
```

**Rule:** Never expose raw exception messages (e.g., `botocore.exceptions.ClientError`).
Map to friendly messages.

**Rule:** The frontend API client has a single response parser that handles both
success and error envelopes.

---

### Principle 8: DynamoDB Reads After Writes Use ConsistentRead

**Rule:** Any API endpoint that writes and then reads (e.g., create → return created
item, or create → list) uses `ConsistentRead=True`.

**Rule:** The repository base class has `read_after_write=True` as default for all
single-item gets. List queries that immediately follow a write also use it.

---

### Principle 9: Terraform Module Defaults Are Production-Safe

**Rule:** S3 buckets always use:
- `block_public_access = true` (never public bucket policies)
- CloudFront OAC for serving (not public read)

**Rule:** Multi-line HCL ternaries are always wrapped in parentheses:
```hcl
local_value = (
  var.flag ? "a" : "b"
)
```

**Rule:** All shell scripts use `[[:space:]]` instead of `\s` for macOS compatibility.

**Rule:** All deployment-unique values (Cognito domain prefix, bucket names) are
auto-generated in scripts. Never require manual placeholder editing.

**Rule:** Cognito callback URLs always include `http://localhost:5173` for local dev.

---

### Principle 10: Two-Pass Deployment for Circular Dependencies

**What:** CloudFront URL is not known until first Terraform apply, but Cognito needs
the callback URL configured. This is a real circular dependency.

**Rule:** The deploy script handles this automatically:
```bash
# Pass 1: Create infra (Cognito gets placeholder callback URL)
terraform apply ...

# Read outputs
CF_DOMAIN=$(terraform output -raw cloudfront_domain)

# Pass 2: Update Cognito callback URLs with real CloudFront domain
terraform apply -var="callback_urls=[\"https://${CF_DOMAIN}\",\"http://localhost:5173\"]"
```

**Rule:** Document all circular dependencies in `docs/Architecture.md` with the
resolution strategy.

---

### Principle 11: Test the Contract, Not Just the Code

**Rule:** The test suite includes **contract tests** that validate:
1. Every route in `routes.yaml` returns the expected response envelope.
2. Every error code in the error enum is tested.
3. Auth enforcement: every `auth: jwt` route returns 401 without a token.
4. CORS: a test sends an OPTIONS preflight and verifies headers.

**Rule:** Use `moto` for DynamoDB mocking. Use stub providers for LLM. Never call
real AWS services in unit tests.

**Rule:** Every entity has these minimum tests:
- CRUD lifecycle (create → read → update → delete)
- User isolation (user A cannot see user B's data)
- Validation (missing required fields, invalid values)
- Pagination (nextToken flow)

---

### Principle 12: Docker Compose Parity with Production

**Rule:** Local dev uses the same Nginx reverse proxy pattern as production:
- Frontend → `localhost:3000` → Nginx → `/api/*` proxied to API container
- Same origin, no CORS needed locally
- This matches the CloudFront → S3 (static) / API Gateway (API) split in production

**Rule:** DynamoDB Local uses `-inMemory` mode (no SQLite volume permission issues).

**Rule:** Docker Compose health checks verify API readiness, not just port availability:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 5s
  retries: 5
```

**Rule:** boto3 clients always have explicit timeouts:
```python
config = Config(connect_timeout=5, read_timeout=10)
```

---

## Part 3: Base Template Pre-Flight Checklist

Before writing any code for a new project, verify these are in place:

```
[ ] routes.yaml exists with all endpoints, methods, and auth levels
[ ] API Gateway module has full CORS config (origins, methods, headers)
[ ] Lambda handler has structured logging configured
[ ] Lambda handler dispatches unauthenticated routes before auth check
[ ] Response envelope is consistent (data/items + meta + error)
[ ] DynamoDB repository uses ConsistentRead for read-after-write
[ ] Terraform modules use auto-generated unique values (no manual placeholders)
[ ] Shell scripts use [[:space:]] not \s
[ ] Shell scripts source shared config.sh for SSM paths
[ ] Deploy script has SSM round-trip validation (read back what was stored)
[ ] S3 bucket uses block_public_access + CloudFront OAC
[ ] Cognito callback URLs include localhost
[ ] deploy script handles two-pass for CloudFront ↔ Cognito circular dep
[ ] Test suite covers: CRUD lifecycle, user isolation, auth enforcement, validation
[ ] LLM/external calls use explicit region_name from env var
[ ] Docker Compose health checks verify API readiness
[ ] boto3 clients have explicit timeouts
```

---

## Part 4: Prompt Instructions for Claude

When building from the base template, include these instructions in the project
`CLAUDE.md` so that Claude (or any AI assistant) follows these patterns:

```markdown
## API Contract Rules

1. Every new endpoint MUST be added to BOTH:
   - `routes.yaml` (source of truth)
   - Terraform `main.tf` api_routes map
   - Lambda handler dispatch table
   If any one is missing, the route will 404 in production.

2. Every response MUST use the standard envelope:
   - Success: `{ "data": {...}, "meta": { "requestId": "..." } }`
   - List:    `{ "items": [...], "meta": { "requestId": "...", "nextToken": "..." } }`
   - Error:   `{ "error": { "code": "...", "message": "..." }, "meta": { "requestId": "..." } }`

3. Never expose raw exception messages in API responses.

4. When adding a custom HTTP header, also add it to:
   - API Gateway CORS `allow_headers`
   - Lambda `_cors_headers()` function

## DynamoDB Rules

5. Use ConsistentRead=True for any read that follows a write.
6. Use simple put_item/update_item. Only use TransactWriteItems when atomicity
   is truly required (and ensure IAM policy includes the permission).
7. Single-table design: PK=USER#{userId}, SK={ENTITY_PREFIX}#{sortable_field}#{id}

## Deployment Rules

8. All SSM paths are defined in scripts/config.sh. Never hardcode paths.
9. When fixing a bug, grep the entire codebase for the same pattern before committing.
10. Shell scripts must work on macOS (BSD) and Linux (GNU):
    - Use [[:space:]] not \s in sed/grep
    - Use $(( )) for arithmetic, not expr
11. Terraform ternaries: always wrap in parentheses if multi-line.
12. Never use public S3 bucket policies. Always CloudFront OAC.

## Testing Rules

13. Every new entity needs: CRUD lifecycle, user isolation, validation, pagination tests.
14. Use moto for DynamoDB mocking. Use stub providers for external APIs.
15. Run `make validate-routes` before committing any route changes.
```
