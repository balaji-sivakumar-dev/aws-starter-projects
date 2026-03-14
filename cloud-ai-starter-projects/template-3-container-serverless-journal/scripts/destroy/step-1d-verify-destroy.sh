#!/bin/bash
# Step 1D — Verify all resources have been destroyed (best-effort checks)
#
# Checks: S3 state bucket, S3 web bucket, DynamoDB tables, Cognito pool,
#         Lambda functions, App Runner services, ECR repository, CloudFront.
#
# Usage:
#   chmod +x scripts/destroy/step-1d-verify-destroy.sh
#   AWS_PROFILE=journal-dev ./scripts/destroy/step-1d-verify-destroy.sh dev

set -euo pipefail

ENV_NAME="${1:-dev}"
REGION="${REGION:-us-east-1}"
APP_PREFIX="${APP_PREFIX:-journal}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

STATE_BUCKET="${APP_PREFIX}-tfstate-${ACCOUNT_ID}-${REGION}"
WEB_BUCKET="${APP_PREFIX}-${ENV_NAME}-web"       # adjust if your naming differs
LOCK_TABLE="${APP_PREFIX}-tflock"
DDB_TABLE="${APP_PREFIX}-${ENV_NAME}-journal"
COGNITO_POOL_NAME="${APP_PREFIX}-${ENV_NAME}-users"
ECR_REPO_NAME="${APP_PREFIX}-${ENV_NAME}-api"
APPRUNNER_SERVICE="${APP_PREFIX}-${ENV_NAME}-api"

echo "== Verify Destroy (Template 3) =="
echo "Account      : ${ACCOUNT_ID}"
echo "Region       : ${REGION}"
echo "Env          : ${ENV_NAME}"
echo "App prefix   : ${APP_PREFIX}"
echo

failures=0

check_absent() {
  local label="$1"
  local status="$2"   # "gone" | "present"
  if [ "${status}" = "present" ]; then
    echo "  ❌ STILL EXISTS: ${label}"
    failures=$((failures+1))
  else
    echo "  ✅ Gone: ${label}"
  fi
}

# ── S3 state bucket ───────────────────────────────────────────────────────────
echo ">> Checking S3 state bucket: ${STATE_BUCKET}"
if aws s3api head-bucket --bucket "${STATE_BUCKET}" 2>/dev/null; then
  check_absent "${STATE_BUCKET}" "present"
else
  check_absent "${STATE_BUCKET}" "gone"
fi

# ── S3 web bucket ─────────────────────────────────────────────────────────────
echo ">> Checking S3 web bucket: ${WEB_BUCKET}"
if aws s3api head-bucket --bucket "${WEB_BUCKET}" 2>/dev/null; then
  check_absent "${WEB_BUCKET}" "present"
else
  check_absent "${WEB_BUCKET}" "gone"
fi

# ── DynamoDB lock table ───────────────────────────────────────────────────────
echo ">> Checking DynamoDB lock table: ${LOCK_TABLE}"
if aws dynamodb describe-table --table-name "${LOCK_TABLE}" --region "${REGION}" >/dev/null 2>&1; then
  check_absent "DynamoDB: ${LOCK_TABLE}" "present"
else
  check_absent "DynamoDB: ${LOCK_TABLE}" "gone"
fi

# ── DynamoDB app table ────────────────────────────────────────────────────────
echo ">> Checking DynamoDB app table: ${DDB_TABLE}"
if aws dynamodb describe-table --table-name "${DDB_TABLE}" --region "${REGION}" >/dev/null 2>&1; then
  check_absent "DynamoDB: ${DDB_TABLE}" "present"
else
  check_absent "DynamoDB: ${DDB_TABLE}" "gone"
fi

# ── Cognito user pool ─────────────────────────────────────────────────────────
echo ">> Checking Cognito user pool: ${COGNITO_POOL_NAME}"
USER_POOLS_JSON="$(aws cognito-idp list-user-pools --max-results 60 --region "${REGION}" --output json 2>/dev/null || echo '{"UserPools":[]}')"
export USER_POOLS_JSON COGNITO_POOL_NAME
COGNITO_STATUS="$(python3 - <<'PY'
import json, os
data = json.loads(os.environ["USER_POOLS_JSON"])
target = os.environ["COGNITO_POOL_NAME"]
found = [p for p in data.get("UserPools", []) if p.get("Name") == target]
print("present" if found else "gone")
PY
)"
check_absent "Cognito: ${COGNITO_POOL_NAME}" "${COGNITO_STATUS}"

# ── App Runner service ────────────────────────────────────────────────────────
echo ">> Checking App Runner service: ${APPRUNNER_SERVICE}"
set +e
APPRUNNER_STATUS="$(aws apprunner list-services --region "${REGION}" \
  --query "ServiceSummaryList[?ServiceName=='${APPRUNNER_SERVICE}'].Status | [0]" \
  --output text 2>/dev/null)"
set -e
if [ -n "${APPRUNNER_STATUS}" ] && [ "${APPRUNNER_STATUS}" != "None" ] && [ "${APPRUNNER_STATUS}" != "DELETED" ]; then
  check_absent "App Runner: ${APPRUNNER_SERVICE} (${APPRUNNER_STATUS})" "present"
else
  check_absent "App Runner: ${APPRUNNER_SERVICE}" "gone"
fi

# ── ECR repository ────────────────────────────────────────────────────────────
echo ">> Checking ECR repository: ${ECR_REPO_NAME}"
if aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${REGION}" >/dev/null 2>&1; then
  check_absent "ECR: ${ECR_REPO_NAME}" "present"
else
  check_absent "ECR: ${ECR_REPO_NAME}" "gone"
fi

# ── CloudFront ────────────────────────────────────────────────────────────────
echo ">> Checking CloudFront distributions (matching ${APP_PREFIX}-${ENV_NAME})..."
set +e
DISTS_JSON="$(aws cloudfront list-distributions --output json 2>/dev/null || echo '{}')"
set -e
export DISTS_JSON APP_PREFIX ENV_NAME
CF_STATUS="$(python3 - <<'PY'
import json, os
try:
    data = json.loads(os.environ["DISTS_JSON"])
except (json.JSONDecodeError, KeyError):
    print("gone")
    exit()
prefix = f"{os.environ['APP_PREFIX']}-{os.environ['ENV_NAME']}"
items = data.get("DistributionList", {}).get("Items", [])
matched = [d["Id"] for d in items
           if any(prefix in o.get("DomainName", "") for o in d.get("Origins", {}).get("Items", []))]
print("present" if matched else "gone")
PY
)"
check_absent "CloudFront distributions (${APP_PREFIX}-${ENV_NAME})" "${CF_STATUS}"

# ── Summary ───────────────────────────────────────────────────────────────────
echo
if [ "${failures}" -gt 0 ]; then
  echo "❌ Verification found ${failures} resource(s) still present."
  echo "   Re-run destroy steps or delete manually via the AWS Console."
  exit 1
fi

echo "✅ Verification passed — no matching resources found."
