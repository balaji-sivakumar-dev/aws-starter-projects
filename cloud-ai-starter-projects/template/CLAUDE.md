# Base Template — Claude Instructions

This file defines **binding rules** for the AWS base template and all projects
derived from it. These rules were extracted from 23 fix commits and 112 tests
across Template 3 (Reflect). See `Lessons-Learned-Template3.md` for full context.

Template plan: `Reusable-Template-Plan.md`

---

## Directory Convention

Every project created from this template follows this structure:

```
template-{name}/
  apps/web/                  # React SPA (Vite)
  services/api/              # Python FastAPI + Core business logic
  services/lambda_api/       # Lambda handler wrapper
  services/workflows/        # [opt-in] Step Functions + AI Gateway
  infra/terraform/
    main.tf                  # Orchestrates modules
    variables.tf
    modules/
      auth/                  # Cognito User Pool + PKCE + pre-signup Lambda
      db/                    # DynamoDB single-table
      compute_lambda/        # Lambda + IAM
      api_edge/              # API Gateway v2 HTTP API + JWT authorizer
      web_hosting/           # S3 + CloudFront OAC
      ai_gateway/            # [opt-in] AI enrichment Lambda
      workflow/              # [opt-in] Step Functions
    environments/
      dev/dev.tfvars.example
  scripts/
    config.sh                # Shared constants (SSM paths, app prefix, region)
    setup/                   # Numbered deployment scripts
    destroy/                 # Teardown scripts
  docs/
    Architecture.md
    Setup.md
  routes.yaml                # Single source of truth for API routes
  Makefile
  docker-compose.yml
  CLAUDE.md                  # Project-specific rules (inherits from this file)
  IMPLEMENTATION_CHECKLIST.md
```

---

## API Contract Rules

### Rule 1: Single Source of Truth for Routes

Every API endpoint MUST be defined in `routes.yaml` at the project root:

```yaml
routes:
  - path: /health
    method: GET
    auth: none
    description: Health check
  - path: /entries
    method: GET
    auth: jwt
    description: List entries with pagination
```

**When adding a new endpoint, update ALL THREE in the same commit:**
1. `routes.yaml` — the source of truth
2. `infra/terraform/main.tf` — the `api_routes` locals map
3. Handler code — Lambda dispatch table OR FastAPI route decorator

If any one is missing, the route will 404 in production. Run `make validate-routes`
before committing route changes.

### Rule 2: Consistent Response Envelope

Every endpoint returns the same envelope regardless of adapter (FastAPI or Lambda):

**Success (single item):**
```json
{
  "data": { "itemId": "...", "title": "...", ... },
  "meta": { "requestId": "uuid" }
}
```

**Success (list):**
```json
{
  "items": [ { ... }, { ... } ],
  "meta": { "requestId": "uuid", "nextToken": "token_or_null" }
}
```

**Error:**
```json
{
  "error": { "code": "VALIDATION_ERROR", "message": "Human-readable message" },
  "meta": { "requestId": "uuid" }
}
```

**Never expose raw exception messages** (e.g., `botocore.exceptions.ClientError`).
Map all external errors to user-friendly messages.

### Rule 3: Standard Error Codes

| Code | HTTP | When |
|------|------|------|
| `VALIDATION_ERROR` | 400 | Invalid input, business rule violation |
| `UNAUTHORIZED` | 401 | Missing or invalid auth token |
| `FORBIDDEN` | 403 | Valid token but insufficient permissions |
| `NOT_FOUND` | 404 | Resource doesn't exist or belongs to another user |
| `CONFLICT` | 409 | Duplicate resource |
| `AI_ERROR` | 502 | LLM/external API failure |
| `INTERNAL_ERROR` | 500 | Unhandled exception (log full traceback) |

### Rule 4: Unauthenticated Routes Are Explicit and First

The Lambda handler dispatch has two phases:

```python
# Phase 1: Unauthenticated routes (BEFORE auth check)
OPEN_ROUTES = {
    ("GET", "/health"): handle_health,
    ("GET", "/config/providers"): handle_config,
}
if (method, path) in OPEN_ROUTES:
    return OPEN_ROUTES[(method, path)](event, request_id)

# Phase 2: Auth check — everything below requires a valid token
user_id = get_user_id(event)

# Phase 3: Authenticated routes
AUTH_ROUTES = { ... }
```

Every route in `routes.yaml` has `auth: none | jwt`. Both API Gateway route config
AND the Lambda handler must respect this field.

### Rule 5: Custom Headers Require CORS Update

When adding ANY custom HTTP header (request or response), also add it to:
1. API Gateway CORS `allow_headers` in `infra/terraform/modules/api_edge/main.tf`
2. Lambda `_cors_headers()` function in the handler
3. The `cors_headers` list in `routes.yaml` (if using route-driven CORS)

---

## CORS Rules

### Rule 6: CORS is Day-Zero Infrastructure

The API Gateway module ships with this config from the first commit:

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

**Never use wildcard patterns** (e.g., `https://*.cloudfront.net`) in `allow_origins`
for API Gateway v2 — it only accepts exact URLs or literal `*`.

---

## DynamoDB Rules

### Rule 7: Single-Table Design Convention

```
PK: USER#{userId}
SK: {ENTITY}#{sortable_field}#{id}     # main record
SK: {ENTITY}ID#{id}                    # lookup by ID
```

Entity prefixes are UPPERCASE and match the domain model name (e.g., `ENTRY#`, `ACCOUNT#`, `TXN#`).

### Rule 8: ConsistentRead After Writes

Any API endpoint that writes and then reads (create → return, create → list) MUST use
`ConsistentRead=True`. DynamoDB eventually consistent reads can miss data written
milliseconds ago.

### Rule 9: Simple Operations First

Use `put_item` / `update_item` / `delete_item` for single-record operations.
Only use `TransactWriteItems` when true multi-record atomicity is required — and
ensure the IAM policy includes `dynamodb:TransactWriteItems`.

---

## Deployment Rules

### Rule 10: Shared Config Script

All SSM paths and deployment constants live in `scripts/config.sh`:

```bash
#!/usr/bin/env bash
# scripts/config.sh — single source of truth for deployment constants
APP_PREFIX="${APP_PREFIX:-myapp}"
ENV="${1:-dev}"
AWS_REGION="${AWS_REGION:-ca-central-1}"

SSM_PREFIX="/${APP_PREFIX}/${ENV}"
SSM_ALLOWED_EMAILS="${SSM_PREFIX}/cognito/allowed_emails"
SSM_ADMIN_EMAILS="${SSM_PREFIX}/cognito/admin_emails"
SSM_GROQ_KEY="${SSM_PREFIX}/ai/groq_api_key"
```

Every setup/destroy script sources this file. Never hardcode SSM paths.

### Rule 11: SSM Round-Trip Validation

`deploy-backend.sh` reads back every SSM value it needs and fails with a clear
message if any are missing:

```bash
source "$(dirname "$0")/config.sh" "$1"

ADMIN_EMAILS=$(aws ssm get-parameter --name "$SSM_ADMIN_EMAILS" --query "Parameter.Value" --output text 2>/dev/null)
if [ -z "$ADMIN_EMAILS" ]; then
  echo "ERROR: SSM parameter $SSM_ADMIN_EMAILS not found. Run 'make secrets' first."
  exit 1
fi
```

### Rule 12: Two-Pass Deploy for Circular Dependencies

CloudFront URL is not known until first `terraform apply`, but Cognito needs
callback URLs. The deploy script handles this automatically:

```bash
# Pass 1: Create infra (Cognito gets placeholder callback URL)
terraform apply ...

# Read outputs
CF_DOMAIN=$(terraform output -raw cloudfront_domain)

# Pass 2: Update Cognito with real CloudFront domain
terraform apply -var="callback_urls=[\"https://${CF_DOMAIN}\",\"http://localhost:5173\"]"
```

Always include `http://localhost:5173` (or local dev port) in callback URLs.

### Rule 13: Auto-Generate Deployment-Unique Values

Never require manual editing of placeholder values. Cognito domain prefix, S3 bucket
suffixes, and other unique identifiers are auto-generated in scripts:

```bash
COGNITO_DOMAIN="${APP_PREFIX}-${ENV}-$(openssl rand -hex 4)"
```

### Rule 14: macOS + Linux Shell Compatibility

- Use `[[:space:]]` not `\s` in sed/grep patterns (BSD sed doesn't support `\s`)
- Use `$(( ))` for arithmetic, not `expr`
- Use `#!/usr/bin/env bash` not `#!/bin/bash`
- Test scripts on macOS before committing

---

## Terraform Rules

### Rule 15: Production-Safe Defaults

- **S3 buckets:** Always `block_public_access = true` + CloudFront OAC. Never public bucket policies.
- **Multi-line ternaries:** Always wrap in parentheses:
  ```hcl
  local_value = (
    var.flag ? "a" : "b"
  )
  ```
- **No duplicate data sources:** Only declare `data "aws_region" "current"` once per module.
- **IAM policies:** Cover all DynamoDB operations the code uses (`PutItem`, `GetItem`, `Query`, `UpdateItem`, `DeleteItem`, `Scan`).

### Rule 16: Validate External Service Config Before Deploy

Bedrock model IDs, embedding dimensions, and region availability should be checked
in a `make validate-config` target before any Terraform runs. A misconfigured model
ID means every AI call fails silently at runtime.

All Bedrock/external API calls use explicit `region_name` from env var:
```python
bedrock = boto3.client("bedrock-runtime", region_name=os.environ["BEDROCK_REGION"])
```
Never default to `AWS_REGION` for cross-region services.

---

## Logging Rules

### Rule 17: Structured Logging from Line One

Every Lambda handler starts with:
```python
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
```

Every handler entry point logs: `method`, `path`, `user_id`, `request_id`.
Every error path logs: `error_code`, `message`, `traceback`.

---

## Testing Rules

### Rule 18: Minimum Test Coverage Per Entity

Every entity (e.g., Entry, Transaction, Account) needs these tests:

| Test | What it validates |
|------|-------------------|
| CRUD lifecycle | create → read → update → delete works end-to-end |
| User isolation | User A cannot see/modify User B's data |
| Auth enforcement | Endpoints return 401 without a valid token |
| Validation | Missing required fields return 400, invalid values return 400 |
| Pagination | `nextToken` flow returns all items across pages |

### Rule 19: Mock Strategy

- **DynamoDB:** Use `moto` (`mock_aws()` context). Import app inside mock context.
- **LLM/External APIs:** Use stub providers injected via factory pattern.
- **Never call real AWS services** in unit tests.

### Rule 20: When Fixing a Bug, Grep First

Before committing a fix, grep the entire codebase for the same pattern:
```bash
grep -r "bedrock-runtime" --include="*.py"
grep -r "dynamodb:" --include="*.tf"
```
Apply the fix everywhere, not just where it was discovered. The Bedrock region fix
was applied to `embeddings.py` but missed in `ai_gateway.py`, requiring a second
fix commit.

---

## Docker / Local Dev Rules

### Rule 21: Local-Production Parity

Local dev uses the same reverse proxy pattern as production:
- Nginx serves frontend at `:3000`, proxies `/api/*` to API at `:8080`
- Same-origin requests — no CORS issues locally
- Matches CloudFront → S3 (static) / API Gateway (API) split in production

### Rule 22: DynamoDB Local Configuration

- Use `-inMemory` mode (no SQLite volume permission issues)
- Health checks verify API readiness, not just TCP port:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    interval: 5s
    retries: 5
  ```
- boto3 clients always have explicit timeouts:
  ```python
  config = Config(connect_timeout=5, read_timeout=10)
  ```

---

## Frontend Rules

### Rule 23: API Client Error Handling

The frontend API client handles both success and error envelopes from a single parser:
```javascript
async function request(method, path, body) {
  const resp = await fetch(...)
  const json = await resp.json()
  if (!resp.ok) throw new ApiError(json.error?.code, json.error?.message, resp.status)
  return json
}
```

### Rule 24: CSS Z-Index Scale

Define a z-index scale as CSS variables to avoid stacking conflicts:
```css
:root {
  --z-dropdown: 100;
  --z-overlay: 200;
  --z-modal: 300;
  --z-toast: 400;
}
```

Use `>=` not `>` when checking "should I show this list" conditions.

---

## Pre-Flight Checklist

Before writing code for any new project from this template, verify:

```
[ ] routes.yaml exists with all endpoints, methods, and auth levels
[ ] API Gateway module has full CORS config (origins, methods, all custom headers)
[ ] Lambda handler has structured logging configured
[ ] Lambda handler dispatches unauthenticated routes before auth check
[ ] Response envelope is consistent (data/items + meta + error)
[ ] DynamoDB repository uses ConsistentRead for read-after-write paths
[ ] Terraform modules use auto-generated unique values (no manual placeholders)
[ ] Shell scripts use [[:space:]] not \s for macOS compatibility
[ ] Shell scripts source shared config.sh for SSM paths
[ ] Deploy script has SSM round-trip validation (reads back stored values)
[ ] S3 bucket uses block_public_access + CloudFront OAC
[ ] Cognito callback URLs include localhost for local dev
[ ] Deploy script handles two-pass for CloudFront <-> Cognito circular dep
[ ] Test suite covers: CRUD lifecycle, user isolation, auth enforcement, validation
[ ] LLM/external calls use explicit region_name from env var
[ ] Docker Compose health checks verify API readiness
[ ] boto3 clients have explicit timeouts
```

---

## Learnings Log

> Add new learnings here as they are discovered. Format:
> `[date] Category: description — what broke, why, and the rule to prevent it.`

- [2026-03-21] Initial extraction from Template 3 — 23 fix commits analyzed, 12 principles
  established. See `Lessons-Learned-Template3.md` for full details.
