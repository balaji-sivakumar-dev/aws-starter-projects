#!/bin/bash
# step-2b-store-secrets.sh
# Store application secrets and config in AWS SSM Parameter Store.
#
# Run ONCE per environment, before step-3a (terraform apply).
# Terraform reads these values from SSM at apply time — secrets never go in tfvars.
#
# Usage:
#   AWS_PROFILE=journal-dev ./scripts/setup/step-2b-store-secrets.sh dev
#
# Reads .env.users from the repo root (copy .env.users.example → .env.users first).
# Format:  email@domain.com=admin|user
#
# What this script creates in SSM:
#   /journal/<env>/cognito/allowed_emails   — all emails (pre-signup Lambda allowlist)
#   /journal/<env>/admin_emails             — admin emails only (Lambda ADMIN_EMAILS env var)
#   /journal/<env>/groq_api_key             — Groq API key (only if LLM_PROVIDER=groq)
#   /journal/<env>/openai_api_key           — OpenAI API key (only if LLM_PROVIDER=openai or EMBEDDING_PROVIDER=openai)

set -euo pipefail

ENV="${1:-dev}"
PROFILE="${AWS_PROFILE:-default}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LLM_PROVIDER="${LLM_PROVIDER:-bedrock}"              # bedrock (default) | openai | groq
EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-bedrock}"  # bedrock (default) | openai
USERS_FILE="$REPO_ROOT/.env.users"

echo "============================================================"
echo "  Storing secrets for env  : $ENV"
echo "  AWS profile              : $PROFILE"
echo "  LLM provider             : $LLM_PROVIDER"
echo "  Embedding provider       : $EMBEDDING_PROVIDER"
echo "  Users file               : $USERS_FILE"
echo "============================================================"

# ── Load from .env.local if present (for GROQ_API_KEY etc.) ──────────────────
ENV_FILE="$REPO_ROOT/.env.local"
if [ -f "$ENV_FILE" ]; then
  echo "  Loading keys from .env.local ..."
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

# ── Helper: store one SecureString parameter ─────────────────────────────────
store_param() {
  local name="$1"
  local value="$2"
  local description="$3"

  aws ssm put-parameter \
    --name "$name" \
    --value "$value" \
    --type "SecureString" \
    --description "$description" \
    --overwrite \
    --profile "$PROFILE" \
    --output text \
    --query "Version" > /dev/null

  echo "  ✅ Stored: $name"
}

# ── Parse .env.users ──────────────────────────────────────────────────────────
echo ""
echo "── User Access List (.env.users) ─────────────────────────────"

ALL_EMAILS=""
ADMIN_EMAILS=""

if [ ! -f "$USERS_FILE" ]; then
  echo "  ⚠️  $USERS_FILE not found."
  echo "  Copy the example file and edit it:"
  echo "    cp .env.users.example .env.users"
  echo "  Then re-run this script."
  echo ""
  echo "  WARNING: The pre-signup Lambda will reject ALL registrations until allowed_emails is set."
  echo "============================================================"
  exit 1
fi

while IFS='=' read -r email role; do
  # Skip blank lines and comments
  [[ -z "$email" || "$email" == \#* ]] && continue
  email="$(echo "$email" | tr '[:upper:]' '[:lower:]' | xargs)"
  role="$(echo "$role" | xargs)"

  if [[ -z "$email" || -z "$role" ]]; then
    continue
  fi

  # Build comma-separated lists
  if [[ -n "$ALL_EMAILS" ]]; then
    ALL_EMAILS="$ALL_EMAILS,$email"
  else
    ALL_EMAILS="$email"
  fi

  if [[ "$role" == "admin" ]]; then
    if [[ -n "$ADMIN_EMAILS" ]]; then
      ADMIN_EMAILS="$ADMIN_EMAILS,$email"
    else
      ADMIN_EMAILS="$email"
    fi
  fi
done < "$USERS_FILE"

if [[ -z "$ALL_EMAILS" ]]; then
  echo "  ⚠️  No valid entries found in $USERS_FILE — check the format (email=admin|user)."
  echo "============================================================"
  exit 1
fi

echo "  Allowed emails : $ALL_EMAILS"
echo "  Admin emails   : ${ADMIN_EMAILS:-<none>}"
echo ""

# ── Store Cognito allowlist ───────────────────────────────────────────────────
store_param \
  "/journal/${ENV}/cognito/allowed_emails" \
  "$ALL_EMAILS" \
  "Comma-separated emails allowed to register in journal-${ENV}"

# ── Store admin emails ────────────────────────────────────────────────────────
if [[ -n "$ADMIN_EMAILS" ]]; then
  store_param \
    "/journal/${ENV}/admin_emails" \
    "$ADMIN_EMAILS" \
    "Comma-separated admin emails for journal-${ENV} (Lambda ADMIN_EMAILS env var)"
else
  echo "  ⚠️  No admin users defined. Admin dashboard will be inaccessible."
  echo "  Add at least one email=admin line to .env.users and re-run."
fi

# ── API keys (only if using external LLM or embedding provider) ───────────────
echo ""
echo "── AI Provider Keys ──────────────────────────────────────────"

NEEDS_OPENAI_KEY=false
[[ "$LLM_PROVIDER" == "openai" ]] && NEEDS_OPENAI_KEY=true
[[ "$EMBEDDING_PROVIDER" == "openai" ]] && NEEDS_OPENAI_KEY=true

if [ "$LLM_PROVIDER" = "groq" ]; then
  echo "  LLM: Groq"
  if [ -z "${GROQ_API_KEY:-}" ]; then
    echo ""
    echo -n "  Enter GROQ_API_KEY (input hidden): "
    read -rs GROQ_API_KEY
    echo ""
  fi
  if [ -z "${GROQ_API_KEY:-}" ]; then
    echo "  ⚠️  GROQ_API_KEY not provided — skipping."
  else
    store_param \
      "/journal/${ENV}/groq_api_key" \
      "$GROQ_API_KEY" \
      "Groq API key for journal-${ENV} AI enrichment"
  fi
elif [ "$NEEDS_OPENAI_KEY" = true ]; then
  echo "  LLM: OpenAI (${LLM_PROVIDER}), Embedding: ${EMBEDDING_PROVIDER}"
  if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo ""
    echo -n "  Enter OPENAI_API_KEY (input hidden): "
    read -rs OPENAI_API_KEY
    echo ""
  fi
  if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "  ⚠️  OPENAI_API_KEY not provided — skipping."
    echo "  OpenAI provider will fail at runtime without this key."
  else
    store_param \
      "/journal/${ENV}/openai_api_key" \
      "$OPENAI_API_KEY" \
      "OpenAI API key for journal-${ENV} (LLM and/or embeddings)"
  fi
else
  echo "  Using Bedrock for both LLM and embeddings — no external API key needed."
  echo "  IAM permissions for bedrock:InvokeModel are managed by Terraform (ai_gateway + compute_lambda modules)."
fi

echo ""
echo "  Done. Next steps:"
echo "  1. Run terraform apply:"
echo "       AWS_PROFILE=$PROFILE ./scripts/setup/step-3a-terraform-apply.sh $ENV"
echo "  2. After deploy, create the admin Cognito user — see docs/AWS-Console-Setup.md step 2"
echo "  3. Admin emails are set from .env.users — no manual tfvars step needed."
echo "============================================================"
