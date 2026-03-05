#!/bin/bash
# Step 4A — Export Terraform outputs to apps/web/.env (repeatable)

set -euo pipefail

# Usage:
#   AWS_PROFILE=journal-dev ./scripts/setup/step-4a-export-outputs-to-env.sh dev

ENV_NAME="${1:-dev}"
TF_DIR="infra/terraform"
BACKEND_FILE="${TF_DIR}/backend.${ENV_NAME}.tfbackend"
OUT_DIR="apps/web"
ENV_FILE="${OUT_DIR}/.env"

if [ ! -d "${TF_DIR}" ]; then
  echo "ERROR: Terraform directory not found: ${TF_DIR}"
  exit 1
fi

if [ ! -f "${BACKEND_FILE}" ]; then
  echo "ERROR: backend config not found: ${BACKEND_FILE}"
  exit 1
fi

pushd "${TF_DIR}" >/dev/null
terraform init -reconfigure -backend-config="$(basename "${BACKEND_FILE}")" >/dev/null

API_BASE_URL="$(terraform output -raw api_base_url)"
COGNITO_DOMAIN="$(terraform output -raw cognito_domain)"
COGNITO_CLIENT_ID="$(terraform output -raw cognito_client_id)"

popd >/dev/null

mkdir -p "${OUT_DIR}"

cat > "${ENV_FILE}" <<EOF_ENV
VITE_API_BASE_URL=${API_BASE_URL}
VITE_COGNITO_DOMAIN=${COGNITO_DOMAIN}
VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
VITE_COGNITO_REDIRECT_URI=http://localhost:5173/callback
VITE_COGNITO_LOGOUT_URI=http://localhost:5173/
EOF_ENV

echo "✅ Wrote ${ENV_FILE}"
