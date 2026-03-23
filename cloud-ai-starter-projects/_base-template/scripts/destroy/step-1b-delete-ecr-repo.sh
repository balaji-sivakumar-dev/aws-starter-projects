#!/bin/bash
# Step 1B — Delete the ECR repository (container / hybrid mode only)
#
# The ECR repository is created by step-3b-build-push-container.sh and is
# managed OUTSIDE of Terraform, so terraform destroy does not remove it.
# Run this only if you used container or hybrid compute_mode.
#
# ⚠️ This permanently deletes all images in the repository.
#
# Usage:
#   chmod +x scripts/destroy/step-1b-delete-ecr-repo.sh
#   AWS_PROFILE={{APP_PREFIX}}-dev ./scripts/destroy/step-1b-delete-ecr-repo.sh dev

set -euo pipefail

ENV_NAME="${1:-dev}"
REGION="${REGION:-us-east-1}"
PROJECT_PREFIX="${PROJECT_PREFIX:-{{APP_PREFIX}}}"

ECR_REPO_NAME="${PROJECT_PREFIX}-${ENV_NAME}-api"

echo "== Delete ECR Repository: {{APP_PREFIX}} =="
echo "Environment : ${ENV_NAME}"
echo "Region      : ${REGION}"
echo "ECR repo    : ${ECR_REPO_NAME}"
echo

# ── Check it exists ───────────────────────────────────────────────────────────
if ! aws ecr describe-repositories \
     --repository-names "${ECR_REPO_NAME}" \
     --region "${REGION}" >/dev/null 2>&1; then
  echo "ECR repository does not exist: ${ECR_REPO_NAME}"
  echo "Nothing to delete."
  exit 0
fi

# ── Count images ──────────────────────────────────────────────────────────────
IMAGE_COUNT="$(aws ecr list-images \
  --repository-name "${ECR_REPO_NAME}" \
  --region "${REGION}" \
  --query 'length(imageIds)' \
  --output text 2>/dev/null || echo 0)"

echo "Images in repository: ${IMAGE_COUNT}"
echo

read -rp "Type DELETE to confirm deleting ECR repository '${ECR_REPO_NAME}' and all ${IMAGE_COUNT} image(s): " CONFIRM
if [ "${CONFIRM}" != "DELETE" ]; then
  echo "Cancelled."
  exit 0
fi

echo ">> Deleting ECR repository (--force removes all images)..."
aws ecr delete-repository \
  --repository-name "${ECR_REPO_NAME}" \
  --region "${REGION}" \
  --force >/dev/null

echo
echo "✅ ECR repository deleted: ${ECR_REPO_NAME}"
