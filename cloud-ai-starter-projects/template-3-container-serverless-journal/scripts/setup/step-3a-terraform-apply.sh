#!/bin/bash
# Step 3A — Terraform init / plan / apply
#
# Works for all compute_mode values (serverless, container, hybrid).
# For container or hybrid mode: run step-3b FIRST to build + push the image,
# then set container_image_uri in your .tfvars before running this script.
#
# Usage:
#   chmod +x scripts/setup/step-3a-terraform-apply.sh
#   AWS_PROFILE=journal-dev ./scripts/setup/step-3a-terraform-apply.sh dev

set -euo pipefail

ENV_NAME="${1:-dev}"
TF_DIR="${TF_DIR:-infra/terraform}"
VAR_FILE="${TF_DIR}/environments/${ENV_NAME}/${ENV_NAME}.tfvars"
REL_VAR_FILE="environments/${ENV_NAME}/${ENV_NAME}.tfvars"
BACKEND_FILE="${TF_DIR}/backend.${ENV_NAME}.tfbackend"
OUT_DIR="${OUT_DIR:-apps/web}"
ENV_FILE="${ENV_FILE:-${OUT_DIR}/.env}"

echo "== Terraform Apply (Template 3) =="
echo "Environment : ${ENV_NAME}"
echo "TF_DIR      : ${TF_DIR}"
echo "VAR_FILE    : ${VAR_FILE}"
echo "BACKEND     : ${BACKEND_FILE}"
echo

# ── Pre-flight checks ─────────────────────────────────────────────────────────
if [ ! -d "${TF_DIR}" ]; then
  echo "ERROR: Terraform directory not found: ${TF_DIR}"
  exit 1
fi

if [ ! -f "${VAR_FILE}" ]; then
  echo "ERROR: tfvars not found: ${VAR_FILE}"
  echo "Tip: cp infra/terraform/environments/dev/dev.tfvars.example ${VAR_FILE}"
  exit 1
fi

if [ ! -f "${BACKEND_FILE}" ]; then
  echo "ERROR: backend config not found: ${BACKEND_FILE}"
  echo "Tip: run step-2-bootstrap-terraform-backend.sh first"
  exit 1
fi

# ── Auto-generate cognito_domain_prefix if empty ──────────────────────────────
COGNITO_PREFIX_CURRENT="$(grep -E '^cognito_domain_prefix' "${VAR_FILE}" | sed 's/.*=[[:space:]]*"\([^"]*\)".*/\1/' || echo "")"

if [[ -z "${COGNITO_PREFIX_CURRENT}" || "${COGNITO_PREFIX_CURRENT}" == *"change-me"* ]]; then
  # openssl rand -hex 6 → 12 lowercase hex chars (cryptographically random, globally unique)
  RAND_SUFFIX="$(openssl rand -hex 6)"
  GENERATED_PREFIX="${PROJECT_PREFIX:-journal}-${ENV_NAME}-${RAND_SUFFIX}"
  echo ">> Auto-generating cognito_domain_prefix: ${GENERATED_PREFIX}"
  # Patch tfvars in-place — replaces the whole cognito_domain_prefix line
  sed -i.bak "s|^cognito_domain_prefix *=.*|cognito_domain_prefix = \"${GENERATED_PREFIX}\"|" "${VAR_FILE}"
  rm -f "${VAR_FILE}.bak"
  echo "   Saved to ${VAR_FILE} (will reuse on re-runs)"
fi

# ── Clear Lambda zip caches ───────────────────────────────────────────────────
# archive_file data sources cache the zip on disk. Without clearing them, a
# change to handler.py may not be picked up by Terraform if the file timestamp
# doesn't match. Always delete before apply so code is always re-packaged.
echo ">> Clearing Lambda zip caches..."
API_ZIP="${TF_DIR}/modules/compute_lambda/.build/api.zip"
AI_ZIP="${TF_DIR}/modules/ai_gateway/.build/ai-gateway.zip"
[ -f "${API_ZIP}" ] && rm -f "${API_ZIP}" && echo "   Removed ${API_ZIP}" || true
[ -f "${AI_ZIP}"  ] && rm -f "${AI_ZIP}"  && echo "   Removed ${AI_ZIP}"  || true
echo

# ── Detect compute_mode from tfvars ──────────────────────────────────────────
COMPUTE_MODE="$(grep -E '^compute_mode' "${VAR_FILE}" | sed 's/.*=[[:space:]]*"\([^"]*\)".*/\1/' || echo "serverless")"
echo "Compute mode: ${COMPUTE_MODE}"

if [ "${COMPUTE_MODE}" = "container" ] || [ "${COMPUTE_MODE}" = "hybrid" ]; then
  CONTAINER_URI="$(grep -E '^container_image_uri' "${VAR_FILE}" | sed 's/.*=[[:space:]]*"\([^"]*\)".*/\1/' || echo "")"
  if [ -z "${CONTAINER_URI}" ]; then
    echo
    echo "WARN: compute_mode=${COMPUTE_MODE} but container_image_uri is empty in ${VAR_FILE}"
    echo "      App Runner service will NOT be created until a valid image URI is set."
    echo "      Run step-3b-build-push-container.sh first, then update ${VAR_FILE} and re-run this script."
    echo
  fi
fi

# ── Terraform pass 1 ──────────────────────────────────────────────────────────
pushd "${TF_DIR}" >/dev/null

echo ">> terraform init"
terraform init -reconfigure -backend-config="$(basename "${BACKEND_FILE}")"

echo ">> terraform plan"
terraform plan -var-file="${REL_VAR_FILE}"

echo ">> terraform apply (pass 1)"
terraform apply -var-file="${REL_VAR_FILE}"

# Read site_url so we can patch Cognito callback URLs
SITE_URL="$(terraform output -raw site_url 2>/dev/null || echo "")"

popd >/dev/null

# ── Patch callback_urls / logout_urls in tfvars with real CloudFront URL ──────
# Cognito requires exact URL match — the default (localhost) won't work after deploy.
if [ -n "${SITE_URL}" ]; then
  CALLBACK_URL="${SITE_URL}/callback"
  LOGOUT_URL="${SITE_URL}/"

  CURRENT_CALLBACK="$(grep -E '^callback_urls' "${VAR_FILE}" | sed 's/.*=[[:space:]]*//' || echo "")"

  # Only patch if CloudFront URL not yet in the list
  if [[ -z "${CURRENT_CALLBACK}" || "${CURRENT_CALLBACK}" != *"${SITE_URL}"* ]]; then
    echo ">> Patching Cognito callback URLs (localhost + CloudFront): ${SITE_URL}"

    # Remove existing lines (if any) then append both localhost + CloudFront
    sed -i.bak '/^callback_urls[[:space:]]*=/d' "${VAR_FILE}"
    sed -i.bak '/^logout_urls[[:space:]]*=/d'   "${VAR_FILE}"
    rm -f "${VAR_FILE}.bak"

    # Both URLs allowed — frontend uses window.location.origin so it picks the right one automatically
    # Ensure there is a trailing newline before appending so the new lines don't
    # merge with the last comment line of the file (which may lack a newline).
    [[ -s "${VAR_FILE}" && "$(tail -c1 "${VAR_FILE}" | wc -l)" -eq 0 ]] && echo "" >> "${VAR_FILE}"
    printf 'callback_urls = ["http://localhost:5173/callback", "%s"]\n' "${CALLBACK_URL}" >> "${VAR_FILE}"
    printf 'logout_urls   = ["http://localhost:5173/", "%s"]\n'         "${LOGOUT_URL}"   >> "${VAR_FILE}"

    echo "   Saved to ${VAR_FILE}"
    echo ">> terraform apply (pass 2 — update Cognito callback URLs)"
    # Use a targeted apply so Terraform is forced to reconcile just the Cognito
    # client. A full apply can miss this update because the state recorded during
    # pass 1 still shows the old (localhost-only) callback_urls value.
    pushd "${TF_DIR}" >/dev/null
    terraform apply -var-file="${REL_VAR_FILE}" \
      -target=module.auth.aws_cognito_user_pool_client.this \
      -auto-approve
    popd >/dev/null
  else
    echo "   Cognito callback URLs already set — skipping pass 2"
    echo "   (re-run step-3a to force update, or run: terraform apply -target=module.auth.aws_cognito_user_pool_client.this)"
  fi
fi

# ── Export outputs to apps/web/.env ──────────────────────────────────────────
echo
echo "== Export Terraform outputs → ${ENV_FILE} =="
mkdir -p "${OUT_DIR}"

pushd "${TF_DIR}" >/dev/null
API_BASE_URL="$(terraform output -raw api_base_url 2>/dev/null || echo "")"
COGNITO_DOMAIN="$(terraform output -raw cognito_domain 2>/dev/null || echo "")"
COGNITO_CLIENT_ID="$(terraform output -raw cognito_client_id 2>/dev/null || echo "")"
SITE_URL="$(terraform output -raw site_url 2>/dev/null || echo "")"
CONTAINER_SERVICE_URL="$(terraform output -raw container_service_url 2>/dev/null || echo "")"
popd >/dev/null

cat > "${ENV_FILE}" <<EOF_ENV
VITE_API_BASE_URL=${API_BASE_URL}
VITE_COGNITO_DOMAIN=${COGNITO_DOMAIN}
VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
VITE_SITE_URL=${SITE_URL}
VITE_AUTH_MODE=cognito
# Container service direct URL (informational — API is accessed via API Gateway above)
CONTAINER_SERVICE_URL=${CONTAINER_SERVICE_URL}
EOF_ENV

echo "✅ Wrote ${ENV_FILE}"
echo
echo "✅ Terraform apply complete for env: ${ENV_NAME}"
echo "   compute_mode: ${COMPUTE_MODE}"
echo "   API endpoint: ${API_BASE_URL}"
echo
echo "Next: deploy the web app →"
echo "   AWS_PROFILE=${AWS_PROFILE:-journal-dev} ./scripts/setup/step-4a-deploy-web-to-s3.sh ${ENV_NAME}"
