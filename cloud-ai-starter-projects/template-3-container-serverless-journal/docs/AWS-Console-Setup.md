# AWS Console Setup — Reflect (Template 3)

Steps that **require the AWS Management Console UI** and cannot be performed via CLI or shell scripts.

> Everything else is automated. Run the setup scripts in order:
> ```
> step-2-bootstrap-terraform-backend.sh   # S3 state + DynamoDB lock
> step-2b-store-secrets.sh                # SSM: email allowlist, API keys
> step-3a-terraform-apply.sh              # Deploy all infrastructure
> step-2c-create-cognito-admin.sh         # Create admin user + set ADMIN_EMAILS
> step-4a-deploy-web-to-s3.sh             # Build + deploy frontend
> ```

---

## Step 1 — AWS Bedrock Model Access (No Action Required for Amazon Models)

**No API keys needed.** Bedrock authenticates via the Lambda's IAM role (`bedrock:InvokeModel` permission), which Terraform provisions automatically.

**Amazon models are auto-enabled on first invocation** — AWS retired the manual model access page. Amazon Nova Lite and Titan Text Embeddings V2 activate automatically when first called in your account. No console action needed.

| Model | Provider | Used for | Access |
|---|---|---|---|
| `amazon.nova-lite-v1:0` | Amazon | LLM — enrichment + insights | Auto-enabled |
| `amazon.titan-embed-text-v2:0` | Amazon | RAG embeddings | Auto-enabled |

> **Anthropic Claude models (optional):** If you change `BEDROCK_MODEL_ID` to an Anthropic Claude model, first-time users may need to submit use case details in the Bedrock console before that specific model activates. Amazon models have no such requirement.

---

## Step 2 — Verify Pre-Signup Lambda Trigger (Recommended Check)

After `step-3a-terraform-apply.sh`, confirm Terraform correctly wired the allowlist Lambda.

**Console path:** Cognito → User Pools → `<your pool>` → User pool properties → Lambda triggers

You should see:
- **Pre sign-up** → `journal-<env>-cognito-pre-signup`

If the trigger is missing, re-run `step-3a-terraform-apply.sh` — Terraform will re-attach it.

**Quick test:**
1. Open the Cognito Hosted UI (URL is in Terraform output `hosted_ui_domain`)
2. Click **Sign up**
3. Enter an email **not** in your `.env.users` file
4. You should see: *"Registration is by invitation only"*

---

## Step 3 — Configure Hosted UI Branding (Optional)

Cognito Hosted UI branding (logo, colours) has no CLI equivalent. This is cosmetic only — the app works without it.

**Console path:** Cognito → User Pools → `<pool>` → Branding → Hosted UI

Options:
- App logo (PNG, max 100 KB)
- Background colour (hex)
- Banner background colour

---

## Quick-Reference Checklist

| # | Step | Required | Done? |
|---|---|---|---|
| 1 | Bedrock model access — auto-enabled; no action needed for Amazon models | Info only | `[x]` |
| 2 | Verify Lambda trigger visible in Cognito → Lambda triggers | Recommended | `[ ]` |
| 3 | Test allowlist rejection with unknown email | Recommended | `[ ]` |
| 4 | Hosted UI branding configured | Optional | `[ ]` |

---

## What the Scripts Handle (No Console Needed)

| What | Script |
|---|---|
| SSM allowlist parameter | `step-2b-store-secrets.sh` |
| Admin email list in SSM | `step-2b-store-secrets.sh` |
| Cognito admin user creation | `step-2c-create-cognito-admin.sh` |
| DynamoDB TTL for rate limiter | Terraform `modules/db` (enabled automatically) |
| All infrastructure (Cognito, DynamoDB, Lambda, API Gateway, S3, CloudFront) | `step-3a-terraform-apply.sh` |
| Frontend build + S3 deploy | `step-4a-deploy-web-to-s3.sh` |
