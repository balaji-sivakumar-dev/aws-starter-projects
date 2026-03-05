#!/bin/bash
set -euo pipefail

# Step 2 (script): Terraform backend bootstrap (repeatable)
# Run this file
# chmod +x scripts/setup/step-2-bootstrap-terraform-backend.sh
# AWS_PROFILE=journal-dev ./scripts/setup/step-2-bootstrap-terraform-backend.sh


# ====== Config (edit these if you want) ======
REGION="${REGION:-ca-central-1}"
PROJECT_PREFIX="${PROJECT_PREFIX:-journal}"
LOCK_TABLE="${LOCK_TABLE:-${PROJECT_PREFIX}-tflock}"

# If AWS_PROFILE is set, aws CLI automatically uses it.
# You can also run: AWS_PROFILE=journal-dev ./script.sh

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
STATE_BUCKET="${STATE_BUCKET:-${PROJECT_PREFIX}-tfstate-${ACCOUNT_ID}-${REGION}}"

echo "== Terraform Backend Bootstrap =="
echo "Account     : ${ACCOUNT_ID}"
echo "Region      : ${REGION}"
echo "State bucket: ${STATE_BUCKET}"
echo "Lock table  : ${LOCK_TABLE}"
echo

# ---------- S3 bucket ----------
echo ">> Ensuring S3 bucket exists..."
if aws s3api head-bucket --bucket "${STATE_BUCKET}" 2>/dev/null; then
  echo "   - Bucket already exists: ${STATE_BUCKET}"
else
  echo "   - Creating bucket: ${STATE_BUCKET}"
  aws s3api create-bucket \
    --bucket "${STATE_BUCKET}" \
    --region "${REGION}" \
    --create-bucket-configuration LocationConstraint="${REGION}"
fi

echo ">> Enabling versioning..."
aws s3api put-bucket-versioning \
  --bucket "${STATE_BUCKET}" \
  --versioning-configuration Status=Enabled

echo ">> Enabling default encryption (AES256)..."
aws s3api put-bucket-encryption \
  --bucket "${STATE_BUCKET}" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# (Optional) Block public access for extra safety
echo ">> Blocking public access (recommended)..."
aws s3api put-public-access-block \
  --bucket "${STATE_BUCKET}" \
  --public-access-block-configuration \
  '{
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
  }'

# ---------- DynamoDB lock table ----------
echo ">> Ensuring DynamoDB lock table exists..."
if aws dynamodb describe-table --table-name "${LOCK_TABLE}" --region "${REGION}" >/dev/null 2>&1; then
  echo "   - Table already exists: ${LOCK_TABLE}"
else
  echo "   - Creating table: ${LOCK_TABLE}"
  aws dynamodb create-table \
    --table-name "${LOCK_TABLE}" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${REGION}" >/dev/null

  echo "   - Waiting for table to become ACTIVE..."
  aws dynamodb wait table-exists --table-name "${LOCK_TABLE}" --region "${REGION}"
fi

echo
echo "✅ Bootstrap complete."
echo
echo "Next: create backend config file with:"
echo "  bucket         = \"${STATE_BUCKET}\""
echo "  dynamodb_table = \"${LOCK_TABLE}\""
echo "  region         = \"${REGION}\""
