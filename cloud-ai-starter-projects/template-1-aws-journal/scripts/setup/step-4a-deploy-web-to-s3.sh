#!/bin/bash
# Step 4A — Deploy the web app to S3 (CloudFront enabled)

set -euo pipefail

# Usage:
#   AWS_PROFILE=journal-dev ./scripts/setup/step-4a-deploy-web-to-s3.sh dev
#
# Assumes you run from repo root.
# chmod +x scripts/setup/step-4a-deploy-web-to-s3.sh

ENV_NAME="${1:-dev}"

TF_DIR="${TF_DIR:-infra/terraform}"
WEB_DIR="${WEB_DIR:-apps/web}"
OUT_DIR="${OUT_DIR:-apps/web}"
ENV_FILE="${ENV_FILE:-${OUT_DIR}/.env}"

echo "== Web Deploy =="
echo "Environment : ${ENV_NAME}"
echo "TF_DIR      : ${TF_DIR}"
echo "WEB_DIR     : ${WEB_DIR}"
echo

if [ ! -d "${TF_DIR}" ]; then
  echo "ERROR: Terraform directory not found: ${TF_DIR}"
  exit 1
fi

if [ ! -d "${WEB_DIR}" ]; then
  echo "ERROR: Web app directory not found: ${WEB_DIR}"
  exit 1
fi

pushd "${TF_DIR}" >/dev/null

echo ">> terraform output (web_bucket_name, site_url)"
WEB_BUCKET_NAME="$(terraform output -raw web_bucket_name)"
SITE_URL="$(terraform output -raw site_url)"
CF_DISTRIBUTION_ID="$(terraform output -raw web_cloudfront_distribution_id || true)"
API_BASE_URL="$(terraform output -raw api_base_url)"
COGNITO_DOMAIN="$(terraform output -raw cognito_domain)"
COGNITO_CLIENT_ID="$(terraform output -raw cognito_client_id)"

popd >/dev/null

if [ -z "${WEB_BUCKET_NAME}" ]; then
  echo "ERROR: web_bucket_name output is empty"
  exit 1
fi

echo "Web bucket : ${WEB_BUCKET_NAME}"
echo "Site URL   : ${SITE_URL}"
if [ -n "${CF_DISTRIBUTION_ID}" ]; then
  echo "CloudFront : ${CF_DISTRIBUTION_ID}"
fi
echo

echo ">> Endpoint check (best-effort)"
set +e
STATUS_CODE="$(curl -s -o /dev/null -w "%{http_code}" "${SITE_URL}/index.html")"
set -e
if [ "${STATUS_CODE}" = "200" ] || [ "${STATUS_CODE}" = "304" ]; then
  echo "OK: ${SITE_URL}/index.html returned ${STATUS_CODE}"
else
  echo "WARN: ${SITE_URL}/index.html returned ${STATUS_CODE} (may take time to propagate)"
fi
echo

pushd "${WEB_DIR}" >/dev/null

echo ">> npm install"
npm install

echo ">> npm run build"
npm run build

if [ ! -d "dist" ]; then
  echo "ERROR: build output not found at ${WEB_DIR}/dist"
  exit 1
fi

echo ">> aws s3 sync dist s3://${WEB_BUCKET_NAME} --delete"
aws s3 sync dist "s3://${WEB_BUCKET_NAME}" --delete

popd >/dev/null

if [ -n "${CF_DISTRIBUTION_ID}" ]; then
  echo
  echo ">> aws cloudfront create-invalidation --distribution-id ${CF_DISTRIBUTION_ID} --paths '/*'"
  aws cloudfront create-invalidation --distribution-id "${CF_DISTRIBUTION_ID}" --paths "/*"
fi

echo
echo "== Export outputs to ${ENV_FILE} =="
mkdir -p "${OUT_DIR}"

LOGIN_REDIRECT_URI="${SITE_URL}/callback"
LOGIN_REDIRECT_URI_ENC="$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "${LOGIN_REDIRECT_URI}")"
LOGIN_URL="https://${COGNITO_DOMAIN}/login?client_id=${COGNITO_CLIENT_ID}&response_type=code&redirect_uri=${LOGIN_REDIRECT_URI_ENC}"

cat > "${ENV_FILE}" <<EOF_ENV
VITE_API_BASE_URL=${API_BASE_URL}
VITE_COGNITO_DOMAIN=${COGNITO_DOMAIN}
VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
VITE_SITE_URL=${SITE_URL}
VITE_CLOUDFRONT_URL=${SITE_URL}
VITE_COGNITO_LOGIN_URL=${LOGIN_URL}
EOF_ENV

echo "✅ Wrote ${ENV_FILE}"

echo
echo "✅ Web deployed to ${SITE_URL}"
