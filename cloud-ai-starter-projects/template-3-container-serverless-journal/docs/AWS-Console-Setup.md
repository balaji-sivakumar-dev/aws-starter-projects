# AWS Console Setup Guide — Reflect (Template 3)

Steps that **cannot** be automated by Terraform or shell scripts and must be performed manually in the AWS Management Console.

---

## Prerequisites

Complete the Terraform deployment first:

```bash
cd infra/terraform
terraform init
terraform apply
```

All resources below assume the stack is deployed. The Terraform outputs you'll need:

| Output | Where to find it |
|---|---|
| `user_pool_id` | `terraform output user_pool_id` |
| `user_pool_client_id` | `terraform output user_pool_client_id` |
| `hosted_ui_domain` | `terraform output hosted_ui_domain` |

---

## Step 1 — Create the User Allowlist in SSM Parameter Store

Terraform deploys the pre-signup Lambda but **does not create the SSM parameter** (it contains email addresses which are not in source control).

**Console path:** Systems Manager → Parameter Store → Create parameter

| Field | Value |
|---|---|
| Name | `/<app_prefix>/<env>/cognito/allowed_emails` |
| Tier | Standard |
| Type | SecureString |
| KMS key | Default (`aws/ssm`) |
| Value | One email per line (or comma-separated). Example: |

```
alice@example.com
bob@example.com
```

**AWS CLI alternative:**

```bash
aws ssm put-parameter \
  --name "/reflect/prod/cognito/allowed_emails" \
  --type SecureString \
  --value "alice@example.com,bob@example.com" \
  --overwrite
```

To add more users later, update the same parameter — no Lambda redeployment needed.

---

## Step 2 — Create the Admin Cognito User

Terraform provisions the User Pool but does not pre-create users. Create the admin account manually.

**Console path:** Cognito → User Pools → `<your pool>` → Users → Create user

| Field | Value |
|---|---|
| Invitation message | Send email invitation |
| Email address | Your admin email (must also be in the SSM allowlist above) |
| Temporary password | Set one; user will be asked to change it on first login |
| Mark email as verified | ✓ Yes |

**AWS CLI alternative:**

```bash
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com Name=email_verified,Value=true Name=given_name,Value=Admin \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS
```

---

## Step 3 — Configure ADMIN_USER_IDS on the API Container

The API uses the `ADMIN_USER_IDS` environment variable to grant admin privileges. The value is the Cognito **sub** (UUID) of the admin user — not their email.

**Find the user sub:**

Console: Cognito → User Pools → Users → click the user → copy the **sub** field.

CLI:
```bash
aws cognito-idp admin-get-user \
  --user-pool-id <USER_POOL_ID> \
  --username admin@example.com \
  --query 'UserAttributes[?Name==`sub`].Value' \
  --output text
```

**Set on the container (ECS / App Runner):**

- **ECS Fargate:** Task Definition → Container → Environment Variables → add `ADMIN_USER_IDS=<sub-uuid>`
- **App Runner:** Service → Configuration → Environment variables → add `ADMIN_USER_IDS=<sub-uuid>`

For multiple admins, use a comma-separated list: `ADMIN_USER_IDS=uuid1,uuid2`

---

## Step 4 — Verify Pre-Signup Lambda is Wired

After `terraform apply`, confirm Cognito is calling the Lambda.

**Console path:** Cognito → User Pools → `<pool>` → User pool properties → Lambda triggers

You should see:
- **Pre sign-up** → `reflect-<env>-cognito-pre-signup`

If missing, re-run `terraform apply` and check for errors in the `aws_lambda_permission` or `lambda_config` resources.

**Test the allowlist:**
1. Open the Hosted UI login page
2. Try registering with an email NOT in the SSM allowlist
3. Cognito should display: *"Registration is by invitation only..."*
4. Try with an allowed email — registration should proceed

---

## Step 5 — Configure Cognito Hosted UI Branding (Optional)

Terraform creates the User Pool domain but does not configure the hosted UI appearance.

**Console path:** Cognito → User Pools → `<pool>` → Branding → Hosted UI

You can set:
- App logo (PNG, max 100 KB)
- Background colour (hex)
- Banner background colour

No functional impact — cosmetic only.

---

## Step 6 — Set Up CloudWatch Alarms (Recommended)

These alarms help catch abuse or runaway costs. Create them in the Console under CloudWatch → Alarms → Create alarm.

| Alarm | Metric | Threshold |
|---|---|---|
| RAG ask rate | Application logs — `rag_ask` count per day | > 100/day |
| Lambda errors | `reflect-<env>-cognito-pre-signup` Errors | > 5 in 5 min |
| DynamoDB consumed capacity | `ConsumedWriteCapacityUnits` on `journal` table | > 500 WCU/hr |

**SNS topic for notifications:**

```bash
aws sns create-topic --name reflect-prod-alerts
aws sns subscribe --topic-arn arn:aws:sns:<region>:<account>:reflect-prod-alerts \
  --protocol email --notification-endpoint your@email.com
```

---

## Step 7 — Enable DynamoDB TTL (for Rate Limiter)

The rate limiter writes items with a `ttl` attribute. Enable TTL so DynamoDB automatically purges expired counters.

**Console path:** DynamoDB → Tables → `journal` → Additional settings → Time to live → Enable

- TTL attribute name: `ttl`

**AWS CLI:**
```bash
aws dynamodb update-time-to-live \
  --table-name journal \
  --time-to-live-specification Enabled=true,AttributeName=ttl
```

---

## Quick-Reference Checklist

| # | Step | Done? |
|---|---|---|
| 1 | SSM allowlist parameter created with admin email | `[ ]` |
| 2 | Admin Cognito user created | `[ ]` |
| 3 | Admin sub UUID noted | `[ ]` |
| 4 | `ADMIN_USER_IDS` env var set on container | `[ ]` |
| 5 | Pre-signup Lambda trigger visible in Cognito | `[ ]` |
| 6 | Allowlist rejection tested | `[ ]` |
| 7 | DynamoDB TTL enabled on `ttl` attribute | `[ ]` |
| 8 | CloudWatch alarms configured (optional) | `[ ]` |
