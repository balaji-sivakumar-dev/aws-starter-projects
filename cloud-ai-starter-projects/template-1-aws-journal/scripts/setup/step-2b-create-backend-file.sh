#!/bin/bash
# Step 2B — Generate backend.dev.tfbackend from AWS account + region

set -euo pipefail

# Usage:
#   AWS_PROFILE=journal-dev ./scripts/setup/step-2b-create-backend-file.sh dev
#
# Optional overrides:
#   REGION=ca-central-1 PROJECT_PREFIX=journal STATE_BUCKET=... LOCK_TABLE=...

ENV_NAME="${1:-dev}"
REGION="${REGION:-}"
TF_DIR="infra/terraform"
TFVARS_FILE="${TF_DIR}/environments/${ENV_NAME}/${ENV_NAME}.tfvars"

if [ -z "${REGION}" ] && [ -f "${TFVARS_FILE}" ]; then
  REGION="$(awk -F"=" \047/^[[:space:]]*aws_region[[:space:]]*=/{gsub(/"/ ,"", $2); gsub(/[[:space:]]/,"", $2); print $2}\047 "${TFVARS_FILE}")"
fi

if [ -z "${REGION}" ]; then
  REGION="ca-central-1"
fi
PROJECT_PREFIX="${PROJECT_PREFIX:-journal}"
LOCK_TABLE="${LOCK_TABLE:-${PROJECT_PREFIX}-tflock}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
STATE_BUCKET="${STATE_BUCKET:-${PROJECT_PREFIX}-tfstate-${ACCOUNT_ID}-${REGION}}"

BACKEND_FILE="${TF_DIR}/backend.${ENV_NAME}.tfbackend"

mkdir -p "${TF_DIR}"

cat > "${BACKEND_FILE}" <<EOF_BACKEND
bucket         = "${STATE_BUCKET}"
key            = "template-1/aws-journal/${ENV_NAME}/terraform.tfstate"
region         = "${REGION}"
dynamodb_table = "${LOCK_TABLE}"
encrypt        = true
EOF_BACKEND

echo "✅ Wrote backend config: ${BACKEND_FILE}"
echo "   bucket         = ${STATE_BUCKET}"
echo "   dynamodb_table = ${LOCK_TABLE}"
echo "   region         = ${REGION}"
