#!/bin/bash
# Step 3C — Terraform init/plan/apply (repeatable)

set -euo pipefail

# Usage:
#   AWS_PROFILE=journal-dev ./scripts/setup/step-3c-terraform-apply.sh dev
#
# Assumes you run from repo root.
# chmod +x scripts/setup/step-3c-terraform-apply.sh

ENV_NAME="${1:-dev}"

TF_DIR="${TF_DIR:-infra/terraform}"
VAR_FILE="${VAR_FILE:-${TF_DIR}/environments/${ENV_NAME}/${ENV_NAME}.tfvars}"
BACKEND_FILE="${BACKEND_FILE:-${TF_DIR}/backend.${ENV_NAME}.tfbackend}"

echo "== Terraform Apply =="
echo "Environment : ${ENV_NAME}"
echo "TF_DIR      : ${TF_DIR}"
echo "VAR_FILE    : ${VAR_FILE}"
echo "BACKEND     : ${BACKEND_FILE}"
echo

if [ ! -d "${TF_DIR}" ]; then
  echo "ERROR: Terraform directory not found: ${TF_DIR}"
  exit 1
fi

if [ ! -f "${VAR_FILE}" ]; then
  echo "ERROR: tfvars not found: ${VAR_FILE}"
  exit 1
fi

if [ ! -f "${BACKEND_FILE}" ]; then
  echo "ERROR: backend config not found: ${BACKEND_FILE}"
  echo "Tip: create it like backend.dev.tfbackend"
  exit 1
fi

pushd "${TF_DIR}" >/dev/null

echo ">> terraform init (with backend config)"
terraform init -reconfigure -backend-config="$(basename "${BACKEND_FILE}")"

echo ">> terraform plan"
terraform plan -var-file="$(basename "${VAR_FILE}")"

echo ">> terraform apply"
terraform apply -var-file="$(basename "${VAR_FILE}")"

popd >/dev/null

echo
echo "✅ Terraform apply complete for env: ${ENV_NAME}"
