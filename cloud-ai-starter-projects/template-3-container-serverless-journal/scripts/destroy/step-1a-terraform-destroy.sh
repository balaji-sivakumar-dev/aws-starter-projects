#!/bin/bash
# Step 1A — Terraform destroy (removes all Terraform-managed resources)
#
# This deletes: DynamoDB table, Cognito user pool, Lambda functions,
# App Runner service (if deployed), API Gateway, S3 web bucket, IAM roles, etc.
#
# This does NOT delete:
#   - The ECR repository (managed outside Terraform) → see step-1b
#   - The Terraform backend (state bucket + lock table) → see step-1c
#
# Usage:
#   chmod +x scripts/destroy/step-1a-terraform-destroy.sh
#   AWS_PROFILE=journal-dev ./scripts/destroy/step-1a-terraform-destroy.sh dev

set -euo pipefail

ENV_NAME="${1:-dev}"
TF_DIR="${TF_DIR:-infra/terraform}"
VAR_FILE="${TF_DIR}/environments/${ENV_NAME}/${ENV_NAME}.tfvars"
REL_VAR_FILE="environments/${ENV_NAME}/${ENV_NAME}.tfvars"
BACKEND_FILE="${TF_DIR}/backend.${ENV_NAME}.tfbackend"

echo "== Terraform Destroy (Template 3) =="
echo "Environment : ${ENV_NAME}"
echo "TF_DIR      : ${TF_DIR}"
echo "VAR_FILE    : ${VAR_FILE}"
echo "BACKEND     : ${BACKEND_FILE}"
echo

# ── Pre-flight ────────────────────────────────────────────────────────────────
if [ ! -d "${TF_DIR}" ]; then
  echo "ERROR: Terraform directory not found: ${TF_DIR}"
  exit 1
fi

if [ ! -f "${VAR_FILE}" ]; then
  echo "ERROR: tfvars not found: ${VAR_FILE}"
  exit 1
fi

if [ ! -f "${BACKEND_FILE}" ]; then
  echo "ERROR: backend config not found: ${BACKEND_FILE}"
  echo "Tip: run step-2-bootstrap-terraform-backend.sh first to regenerate it"
  exit 1
fi

# ── Terraform ─────────────────────────────────────────────────────────────────
pushd "${TF_DIR}" >/dev/null

echo ">> terraform init (to ensure backend is configured)"
terraform init -reconfigure -backend-config="$(basename "${BACKEND_FILE}")"

echo ">> terraform destroy"
terraform destroy -var-file="${REL_VAR_FILE}" -auto-approve

popd >/dev/null

# ── Reset tfvars so the next rebuild generates fresh values ───────────────────
# cognito_domain_prefix: AWS holds deleted Cognito domains for ~60 days so the
#   old prefix cannot be reused. Clear it so step-3a auto-generates a new one.
# callback_urls / logout_urls: CloudFront URL will be different on rebuild.
#   Remove them so step-3a patches them with the new distribution URL.
echo ">> Resetting tfvars for clean rebuild..."

COGNITO_PLACEHOLDER="journal-${ENV_NAME}-change-me"

sed -i.bak "s|^cognito_domain_prefix *=.*|cognito_domain_prefix = \"${COGNITO_PLACEHOLDER}\"|" "${VAR_FILE}"
sed -i.bak '/^callback_urls[[:space:]]*=/d' "${VAR_FILE}"
sed -i.bak '/^logout_urls[[:space:]]*=/d'   "${VAR_FILE}"
rm -f "${VAR_FILE}.bak"

echo "   cognito_domain_prefix → placeholder (step-3a will auto-generate a new one)"
echo "   callback_urls + logout_urls removed  (step-3a will patch with new CloudFront URL)"

# ── Clear Lambda zip caches ───────────────────────────────────────────────────
echo ">> Clearing Lambda zip caches..."
API_ZIP="${TF_DIR}/modules/compute_lambda/.build/api.zip"
AI_ZIP="${TF_DIR}/modules/ai_gateway/.build/ai-gateway.zip"
PRE_SIGNUP_ZIP="${TF_DIR}/modules/auth/lambda/pre_signup.zip"
[ -f "${API_ZIP}"        ] && rm -f "${API_ZIP}"        && echo "   Removed ${API_ZIP}"        || true
[ -f "${AI_ZIP}"         ] && rm -f "${AI_ZIP}"         && echo "   Removed ${AI_ZIP}"         || true
[ -f "${PRE_SIGNUP_ZIP}" ] && rm -f "${PRE_SIGNUP_ZIP}" && echo "   Removed ${PRE_SIGNUP_ZIP}" || true

echo
echo "✅ Terraform-managed resources destroyed for env: ${ENV_NAME}"
echo
echo "Remaining manual steps (if applicable):"
echo "  • ECR repository  → run step-1b-delete-ecr-repo.sh ${ENV_NAME}"
echo "  • TF backend      → run step-1c-delete-terraform-backend.sh"
echo "  • Verify          → run step-1d-verify-destroy.sh ${ENV_NAME}"
echo
echo "Ready to rebuild from scratch:"
echo "  1. AWS_PROFILE=${AWS_PROFILE:-journal-dev} ./scripts/setup/step-2b-store-secrets.sh ${ENV_NAME}"
echo "  2. AWS_PROFILE=${AWS_PROFILE:-journal-dev} ./scripts/setup/step-3a-terraform-apply.sh ${ENV_NAME}"
echo "  3. AWS_PROFILE=${AWS_PROFILE:-journal-dev} ./scripts/setup/step-4a-deploy-web-to-s3.sh ${ENV_NAME}"
