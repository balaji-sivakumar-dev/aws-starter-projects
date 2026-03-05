#!/bin/bash
# Step 1C — Verify destroy (best-effort checks)

set -euo pipefail

# Usage:
#   AWS_PROFILE=journal-dev ./scripts/destroy/step-1c-verify-destroy.sh dev
#
# Assumes you run from repo root.
# chmod +x scripts/destroy/step-1c-verify-destroy.sh

ENV_NAME="${1:-dev}"
REGION="${REGION:-ca-central-1}"
APP_PREFIX="${APP_PREFIX:-journal}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

STATE_BUCKET="${APP_PREFIX}-tfstate-${ACCOUNT_ID}-${REGION}"
WEB_BUCKET="${APP_PREFIX}-${ENV_NAME}-web-${REGION}-${ACCOUNT_ID}"
LOCK_TABLE="${APP_PREFIX}-tflock"
DDB_TABLE="${APP_PREFIX}-${ENV_NAME}-journal"
COGNITO_POOL_NAME="${APP_PREFIX}-${ENV_NAME}-users"
WEBSITE_ORIGIN="${WEB_BUCKET}.s3-website-${REGION}.amazonaws.com"

echo "== Verify Destroy =="
echo "Account      : ${ACCOUNT_ID}"
echo "Region       : ${REGION}"
echo "Env          : ${ENV_NAME}"
echo "App prefix   : ${APP_PREFIX}"
echo "State bucket : ${STATE_BUCKET}"
echo "Web bucket   : ${WEB_BUCKET}"
echo "Lock table   : ${LOCK_TABLE}"
echo "DDB table    : ${DDB_TABLE}"
echo "Cognito pool : ${COGNITO_POOL_NAME}"
echo

failures=0

echo ">> Checking S3 state bucket..."
if aws s3api head-bucket --bucket "${STATE_BUCKET}" 2>/dev/null; then
  echo "ERROR: State bucket still exists: ${STATE_BUCKET}"
  failures=$((failures+1))
else
  echo "OK: State bucket not found."
fi

echo ">> Checking S3 web bucket..."
if aws s3api head-bucket --bucket "${WEB_BUCKET}" 2>/dev/null; then
  echo "ERROR: Web bucket still exists: ${WEB_BUCKET}"
  failures=$((failures+1))
else
  echo "OK: Web bucket not found."
fi

echo ">> Checking DynamoDB lock table..."
if aws dynamodb describe-table --table-name "${LOCK_TABLE}" --region "${REGION}" >/dev/null 2>&1; then
  echo "ERROR: Lock table still exists: ${LOCK_TABLE}"
  failures=$((failures+1))
else
  echo "OK: Lock table not found."
fi

echo ">> Checking DynamoDB app table..."
if aws dynamodb describe-table --table-name "${DDB_TABLE}" --region "${REGION}" >/dev/null 2>&1; then
  echo "ERROR: App table still exists: ${DDB_TABLE}"
  failures=$((failures+1))
else
  echo "OK: App table not found."
fi

echo ">> Checking Cognito user pool..."
USER_POOLS_JSON="$(aws cognito-idp list-user-pools --max-results 60 --region "${REGION}" --output json)"
export USER_POOLS_JSON COGNITO_POOL_NAME
python3 - <<'PY'
import json, os, sys
data = json.loads(os.environ["USER_POOLS_JSON"])
target = os.environ["COGNITO_POOL_NAME"]
found = [p for p in data.get("UserPools", []) if p.get("Name") == target]
if found:
    print(f"FOUND: {target}")
    sys.exit(1)
print("OK: Cognito user pool not found.")
PY
if [ $? -ne 0 ]; then
  failures=$((failures+1))
fi

echo ">> Checking CloudFront distributions (origin match)..."
set +e
DISTS_JSON="$(aws cloudfront list-distributions --output json 2>/dev/null)"
CF_STATUS=$?
set -e
if [ ${CF_STATUS} -ne 0 ] || [ -z "${DISTS_JSON}" ]; then
  echo "WARN: CloudFront list-distributions failed or returned empty output. Skipping CloudFront check."
else
  export DISTS_JSON WEBSITE_ORIGIN
  python3 - <<'PY'
import json, os, sys
try:
    data = json.loads(os.environ["DISTS_JSON"])
except json.JSONDecodeError:
    print("WARN: CloudFront output was not valid JSON. Skipping CloudFront check.")
    sys.exit(0)
origin = os.environ["WEBSITE_ORIGIN"]
items = data.get("DistributionList", {}).get("Items", [])
matched = []
for d in items:
    for o in d.get("Origins", {}).get("Items", []):
        if o.get("DomainName") == origin:
            matched.append(d.get("Id"))
if matched:
    print("FOUND: CloudFront distributions with S3 website origin:", ", ".join(matched))
    sys.exit(1)
print("OK: No CloudFront distributions found for S3 website origin.")
PY
  if [ $? -ne 0 ]; then
    failures=$((failures+1))
  fi
fi

echo
if [ "${failures}" -gt 0 ]; then
  echo "❌ Verification failed with ${failures} remaining resources."
  exit 1
fi

echo "✅ Verification passed. No matching resources found."
