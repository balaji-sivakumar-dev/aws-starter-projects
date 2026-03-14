#!/bin/bash
# Step 2 — Bootstrap Terraform backend (S3 state bucket + DynamoDB lock table)
#
# Run once per AWS account/region. Safe to re-run — checks before creating.
#
# Usage:
#   chmod +x scripts/setup/step-2-bootstrap-terraform-backend.sh
#   AWS_PROFILE=journal-dev ./scripts/setup/step-2-bootstrap-terraform-backend.sh dev

set -euo pipefail

ENV_NAME="${1:-dev}"
REGION="${REGION:-us-east-1}"
PROJECT_PREFIX="${PROJECT_PREFIX:-journal}"
LOCK_TABLE="${LOCK_TABLE:-${PROJECT_PREFIX}-tflock}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
STATE_BUCKET="${STATE_BUCKET:-${PROJECT_PREFIX}-tfstate-${ACCOUNT_ID}-${REGION}}"

echo "== Terraform Backend Bootstrap (Template 3) =="
echo "Account     : ${ACCOUNT_ID}"
echo "Region      : ${REGION}"
echo "State bucket: ${STATE_BUCKET}"
echo "Lock table  : ${LOCK_TABLE}"
echo

# ── S3 state bucket ──────────────────────────────────────────────────────────
echo ">> Ensuring S3 state bucket exists..."
if aws s3api head-bucket --bucket "${STATE_BUCKET}" 2>/dev/null; then
  echo "   Already exists: ${STATE_BUCKET}"
else
  echo "   Creating: ${STATE_BUCKET}"
  if [ "${REGION}" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "${STATE_BUCKET}" --region "${REGION}"
  else
    aws s3api create-bucket \
      --bucket "${STATE_BUCKET}" \
      --region "${REGION}" \
      --create-bucket-configuration LocationConstraint="${REGION}"
  fi
fi

echo ">> Enabling versioning..."
aws s3api put-bucket-versioning \
  --bucket "${STATE_BUCKET}" \
  --versioning-configuration Status=Enabled

echo ">> Enabling default encryption (AES-256)..."
aws s3api put-bucket-encryption \
  --bucket "${STATE_BUCKET}" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

echo ">> Blocking public access..."
aws s3api put-public-access-block \
  --bucket "${STATE_BUCKET}" \
  --public-access-block-configuration \
  '{
    "BlockPublicAcls":true,
    "IgnorePublicAcls":true,
    "BlockPublicPolicy":true,
    "RestrictPublicBuckets":true
  }'

# ── DynamoDB lock table ───────────────────────────────────────────────────────
echo ">> Ensuring DynamoDB lock table exists..."
if aws dynamodb describe-table --table-name "${LOCK_TABLE}" --region "${REGION}" >/dev/null 2>&1; then
  echo "   Already exists: ${LOCK_TABLE}"
else
  echo "   Creating: ${LOCK_TABLE}"
  aws dynamodb create-table \
    --table-name "${LOCK_TABLE}" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${REGION}" >/dev/null
  echo "   Waiting for table to become ACTIVE..."
  aws dynamodb wait table-exists --table-name "${LOCK_TABLE}" --region "${REGION}"
fi

# ── Write .tfbackend config ───────────────────────────────────────────────────
TF_DIR="infra/terraform"
BACKEND_FILE="${TF_DIR}/backend.${ENV_NAME}.tfbackend"
mkdir -p "${TF_DIR}"

cat > "${BACKEND_FILE}" <<EOF_BACKEND
bucket         = "${STATE_BUCKET}"
key            = "template-3/container-serverless-journal/${ENV_NAME}/terraform.tfstate"
region         = "${REGION}"
dynamodb_table = "${LOCK_TABLE}"
encrypt        = true
EOF_BACKEND

echo
echo "✅ Bootstrap complete."
echo "✅ Wrote backend config: ${BACKEND_FILE}"
echo
echo "Next: copy and fill in the tfvars, then run step-3a or step-3b."
echo "   cp infra/terraform/environments/dev/dev.tfvars.example infra/terraform/environments/${ENV_NAME}/${ENV_NAME}.tfvars"
