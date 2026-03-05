#!/bin/bash
# Step 3A — Terraform init/plan/apply (repeatable)

set -euo pipefail

# Usage:
#   AWS_PROFILE=journal-dev ./scripts/setup/step-3a-terraform-apply.sh dev
#
# Assumes you run from repo root.
# chmod +x scripts/setup/step-3a-terraform-apply.sh

ENV_NAME="${1:-dev}"

TF_DIR="${TF_DIR:-infra/terraform}"
VAR_FILE="${VAR_FILE:-${TF_DIR}/environments/${ENV_NAME}/${ENV_NAME}.tfvars}"
REL_VAR_FILE="environments/${ENV_NAME}/${ENV_NAME}.tfvars"
BACKEND_FILE="${BACKEND_FILE:-${TF_DIR}/backend.${ENV_NAME}.tfbackend}"
OUT_DIR="${OUT_DIR:-apps/web}"
ENV_FILE="${ENV_FILE:-${OUT_DIR}/.env}"

echo "== Terraform Apply =="
echo "Environment : ${ENV_NAME}"
echo "TF_DIR      : ${TF_DIR}"
echo "VAR_FILE    : ${VAR_FILE}"
echo "BACKEND     : ${BACKEND_FILE}"
echo

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
  echo "Tip: create it like backend.dev.tfbackend"
  exit 1
fi

pushd "${TF_DIR}" >/dev/null

echo ">> terraform init (with backend config)"
terraform init -reconfigure -backend-config="$(basename "${BACKEND_FILE}")"

echo ">> terraform plan"
terraform plan -var-file="${REL_VAR_FILE}"

echo ">> terraform apply"
terraform apply -var-file="${REL_VAR_FILE}"

popd >/dev/null

echo
echo "== Export outputs to ${ENV_FILE} =="
mkdir -p "${OUT_DIR}"

pushd "${TF_DIR}" >/dev/null
API_BASE_URL="$(terraform output -raw api_base_url)"
COGNITO_DOMAIN="$(terraform output -raw cognito_domain)"
COGNITO_CLIENT_ID="$(terraform output -raw cognito_client_id)"
SITE_URL="$(terraform output -raw site_url)"
popd >/dev/null

cat > "${ENV_FILE}" <<EOF_ENV
VITE_API_BASE_URL=${API_BASE_URL}
VITE_COGNITO_DOMAIN=${COGNITO_DOMAIN}
VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
VITE_SITE_URL=${SITE_URL}
EOF_ENV

echo "✅ Wrote ${ENV_FILE}"

echo
echo "✅ Terraform apply complete for env: ${ENV_NAME}"
echo "Next: deploy the web app to S3 with scripts/setup/step-4a-deploy-web-to-s3.sh ${ENV_NAME}"
