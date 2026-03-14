#!/bin/bash
# Step 3B — Build and push the API Docker image to ECR (container / hybrid mode only)
#
# This step is ONLY required if compute_mode = "container" or "hybrid".
# For serverless mode, skip this step entirely.
#
# What this script does:
#   1. Creates an ECR repository if it doesn't already exist
#   2. Authenticates Docker with ECR
#   3. Builds the API image from services/api/
#   4. Tags and pushes to ECR
#   5. Prints the full image URI to copy into your .tfvars
#
# After running this script, update infra/terraform/environments/<env>/<env>.tfvars:
#   container_image_uri = "<printed URI>"
# Then run step-3a-terraform-apply.sh to create the App Runner service.
#
# Usage:
#   chmod +x scripts/setup/step-3b-build-push-container.sh
#   AWS_PROFILE=journal-dev ./scripts/setup/step-3b-build-push-container.sh [dev]
#
# Optional env vars:
#   REGION            — AWS region (default: us-east-1)
#   PROJECT_PREFIX    — resource name prefix (default: journal)
#   IMAGE_TAG         — Docker image tag (default: latest)
#   PLATFORM          — Docker build platform (default: linux/amd64 for App Runner)

set -euo pipefail

ENV_NAME="${1:-dev}"
REGION="${REGION:-us-east-1}"
PROJECT_PREFIX="${PROJECT_PREFIX:-journal}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"    # App Runner requires amd64

ECR_REPO_NAME="${PROJECT_PREFIX}-${ENV_NAME}-api"
API_DIR="services/api"

echo "== Build + Push Container Image (Template 3) =="
echo "Environment : ${ENV_NAME}"
echo "Region      : ${REGION}"
echo "ECR repo    : ${ECR_REPO_NAME}"
echo "Image tag   : ${IMAGE_TAG}"
echo "Platform    : ${PLATFORM}"
echo

# ── Pre-flight ────────────────────────────────────────────────────────────────
if [ ! -f "${API_DIR}/Dockerfile" ]; then
  echo "ERROR: Dockerfile not found at ${API_DIR}/Dockerfile"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found. Install Docker Desktop first."
  exit 1
fi

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
FULL_IMAGE_URI="${ECR_REGISTRY}/${ECR_REPO_NAME}:${IMAGE_TAG}"

echo "ECR registry: ${ECR_REGISTRY}"
echo "Full URI    : ${FULL_IMAGE_URI}"
echo

# ── Create ECR repository if it doesn't exist ─────────────────────────────────
echo ">> Ensuring ECR repository exists..."
if aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${REGION}" >/dev/null 2>&1; then
  echo "   Already exists: ${ECR_REPO_NAME}"
else
  echo "   Creating: ${ECR_REPO_NAME}"
  aws ecr create-repository \
    --repository-name "${ECR_REPO_NAME}" \
    --region "${REGION}" \
    --image-scanning-configuration scanOnPush=true \
    --image-tag-mutability MUTABLE >/dev/null
fi

# ── Authenticate Docker with ECR ──────────────────────────────────────────────
echo ">> Authenticating Docker with ECR..."
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

# ── Build image ───────────────────────────────────────────────────────────────
echo ">> Building Docker image (platform=${PLATFORM})..."
docker build \
  --platform "${PLATFORM}" \
  --tag "${FULL_IMAGE_URI}" \
  "${API_DIR}"

# ── Push image ────────────────────────────────────────────────────────────────
echo ">> Pushing image to ECR..."
docker push "${FULL_IMAGE_URI}"

echo
echo "✅ Image pushed: ${FULL_IMAGE_URI}"
echo
echo "══════════════════════════════════════════════════════════════"
echo "  Next: update your tfvars and run terraform apply"
echo
echo "  1. Open  infra/terraform/environments/${ENV_NAME}/${ENV_NAME}.tfvars"
echo "  2. Set   container_image_uri = \"${FULL_IMAGE_URI}\""
echo "  3. Set   compute_mode        = \"container\"   # or \"hybrid\""
echo "  4. Run   ./scripts/setup/step-3a-terraform-apply.sh ${ENV_NAME}"
echo "══════════════════════════════════════════════════════════════"
