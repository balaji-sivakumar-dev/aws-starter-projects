#!/bin/bash
# Step 1A — Destroy all Terraform-created resources (recommended “cleanup”)

set -euo pipefail

# Usage:
#   AWS_PROFILE=journal-dev ./scripts/destroy/step-1a-terraform-destroy.sh dev
#
# Assumes you run from repo root.
# chmod +x scripts/destroy/step-1a-terraform-destroy.sh
# AWS_PROFILE=journal-dev ./scripts/destroy/step-1a-terraform-destroy.sh dev


ENV_NAME="${1:-dev}"

TF_DIR="${TF_DIR:-infra/terraform}"
VAR_FILE="${VAR_FILE:-${TF_DIR}/environments/${ENV_NAME}/${ENV_NAME}.tfvars}"
REL_VAR_FILE="environments/${ENV_NAME}/${ENV_NAME}.tfvars"
BACKEND_FILE="${BACKEND_FILE:-${TF_DIR}/backend.${ENV_NAME}.tfbackend}"

echo "== Terraform Destroy =="
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

echo ">> terraform init (to ensure backend is configured)"
terraform init -reconfigure -backend-config="$(basename "${BACKEND_FILE}")"

echo ">> terraform destroy"
terraform destroy -var-file="${REL_VAR_FILE}" -auto-approve

popd >/dev/null

echo
echo "✅ Terraform-managed resources destroyed for env: ${ENV_NAME}"
echo "Note: This does NOT delete the backend (state bucket + lock table)."
