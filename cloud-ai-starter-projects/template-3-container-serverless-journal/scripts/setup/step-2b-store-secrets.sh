#!/bin/bash
# step-2b-store-secrets.sh
# Store application secrets in AWS SSM Parameter Store (SecureString).
#
# Run ONCE per environment, before step-3a (terraform apply).
# Terraform reads these values from SSM at apply time — secrets never go in tfvars.
#
# Usage:
#   AWS_PROFILE=journal-dev ./scripts/setup/step-2b-store-secrets.sh dev
#
# Keys are loaded from .env.local if it exists; otherwise you are prompted.

set -euo pipefail

ENV="${1:-dev}"
PROFILE="${AWS_PROFILE:-default}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "============================================================"
echo "  Storing secrets for env : $ENV"
echo "  AWS profile             : $PROFILE"
echo "============================================================"

# ── Load from .env.local if present ──────────────────────────────────────────
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

# ── Groq API key ─────────────────────────────────────────────────────────────
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

# ── Add more secrets here as needed ──────────────────────────────────────────
# Example:
# if [ -n "${OPENAI_API_KEY:-}" ]; then
#   store_param "/journal/${ENV}/openai_api_key" "$OPENAI_API_KEY" "OpenAI API key"
# fi

echo ""
echo "  Done. Run terraform apply next:"
echo "    AWS_PROFILE=$PROFILE ./scripts/setup/step-3a-terraform-apply.sh $ENV"
echo "============================================================"
