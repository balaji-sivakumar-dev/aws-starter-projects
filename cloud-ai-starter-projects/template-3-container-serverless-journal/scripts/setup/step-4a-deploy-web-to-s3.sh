#!/bin/bash
# Step 4A — Build the React web app and deploy to S3 (+ CloudFront invalidation)
#
# Reads Terraform outputs for bucket name, API URL, and Cognito config.
# Writes apps/web/.env, runs npm build, syncs to S3, and invalidates CloudFront.
#
# Usage:
#   chmod +x scripts/setup/step-4a-deploy-web-to-s3.sh
#   AWS_PROFILE=journal-dev ./scripts/setup/step-4a-deploy-web-to-s3.sh dev

set -euo pipefail

ENV_NAME="${1:-dev}"
TF_DIR="${TF_DIR:-infra/terraform}"
WEB_DIR="${WEB_DIR:-apps/web}"
ENV_FILE="${ENV_FILE:-${WEB_DIR}/.env}"

echo "== Web Deploy (Template 3) =="
echo "Environment : ${ENV_NAME}"
echo "TF_DIR      : ${TF_DIR}"
echo "WEB_DIR     : ${WEB_DIR}"
echo

# ── Pre-flight ────────────────────────────────────────────────────────────────
if [ ! -d "${TF_DIR}" ]; then
  echo "ERROR: Terraform directory not found: ${TF_DIR}"
  exit 1
fi

if [ ! -d "${WEB_DIR}" ]; then
  echo "ERROR: Web app directory not found: ${WEB_DIR}"
  exit 1
fi

# ── Read Terraform outputs ─────────────────────────────────────────────────────
pushd "${TF_DIR}" >/dev/null

echo ">> Reading Terraform outputs..."
WEB_BUCKET_NAME="$(terraform output -raw web_bucket_name 2>/dev/null || echo "")"
SITE_URL="$(terraform output -raw site_url 2>/dev/null || echo "")"
API_BASE_URL="$(terraform output -raw api_base_url 2>/dev/null || echo "")"
COGNITO_DOMAIN="$(terraform output -raw cognito_domain 2>/dev/null || echo "")"
COGNITO_CLIENT_ID="$(terraform output -raw cognito_client_id 2>/dev/null || echo "")"
CF_DISTRIBUTION_ID="$(terraform output -raw cloudfront_distribution_id 2>/dev/null || echo "")"

popd >/dev/null

if [ -z "${WEB_BUCKET_NAME}" ]; then
  echo "ERROR: web_bucket_name output is empty — has terraform apply been run?"
  exit 1
fi

echo "Web bucket  : ${WEB_BUCKET_NAME}"
echo "Site URL    : ${SITE_URL}"
echo "API URL     : ${API_BASE_URL}"
[ -n "${CF_DISTRIBUTION_ID}" ] && echo "CloudFront  : ${CF_DISTRIBUTION_ID}"
echo

# ── Write apps/web/.env ──────────────────────────────────────────────────────
LOGIN_REDIRECT_URI="${SITE_URL}/callback"
LOGIN_REDIRECT_URI_ENC="$(python3 -c \
  'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' \
  "${LOGIN_REDIRECT_URI}")"
LOGIN_URL="https://${COGNITO_DOMAIN}/login?client_id=${COGNITO_CLIENT_ID}&response_type=code&redirect_uri=${LOGIN_REDIRECT_URI_ENC}"

cat > "${ENV_FILE}" <<EOF_ENV
VITE_API_BASE_URL=${API_BASE_URL}
VITE_COGNITO_DOMAIN=${COGNITO_DOMAIN}
VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
VITE_SITE_URL=${SITE_URL}
VITE_CLOUDFRONT_URL=${SITE_URL}
VITE_AUTH_MODE=cognito
VITE_COGNITO_LOGIN_URL=${LOGIN_URL}
EOF_ENV

echo "✅ Wrote ${ENV_FILE}"

# ── npm install + build ───────────────────────────────────────────────────────
pushd "${WEB_DIR}" >/dev/null

echo ">> npm install"
npm install

echo ">> npm run build"
npm run build

if [ ! -d "dist" ]; then
  echo "ERROR: build output not found at ${WEB_DIR}/dist"
  exit 1
fi

# ── Sync to S3 ────────────────────────────────────────────────────────────────
echo ">> aws s3 sync dist → s3://${WEB_BUCKET_NAME}"
aws s3 sync dist "s3://${WEB_BUCKET_NAME}" --delete

popd >/dev/null

# ── CloudFront invalidation ───────────────────────────────────────────────────
if [ -n "${CF_DISTRIBUTION_ID}" ]; then
  echo ">> CloudFront invalidation: ${CF_DISTRIBUTION_ID}"
  aws cloudfront create-invalidation \
    --distribution-id "${CF_DISTRIBUTION_ID}" \
    --paths "/*"
fi

# ── Smoke check ───────────────────────────────────────────────────────────────
echo
echo ">> Endpoint check (best-effort)..."
set +e
STATUS_CODE="$(curl -s -o /dev/null -w "%{http_code}" "${SITE_URL}/index.html")"
set -e
if [ "${STATUS_CODE}" = "200" ] || [ "${STATUS_CODE}" = "304" ]; then
  echo "OK: ${SITE_URL}/index.html → ${STATUS_CODE}"
else
  echo "WARN: ${SITE_URL}/index.html → ${STATUS_CODE} (may take a few minutes to propagate)"
fi

echo
echo "✅ Web deployed to ${SITE_URL}"
