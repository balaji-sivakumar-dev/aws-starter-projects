#!/bin/bash
# Step 3C — Deploy backend changes only (Lambda code + IAM + Step Functions)
#
# Use this for iterative backend changes that do NOT require a full destroy/rebuild.
# It clears the Lambda zip caches so Terraform always re-packages the latest code,
# then runs targeted applies for:
#   • API Lambda         (handler.py changes)
#   • AI Gateway Lambda  (ai_gateway.py changes, IAM policy, env vars)
#   • Step Functions     (state machine ASL definition changes)
#
# Does NOT touch: Cognito, DynamoDB, API Gateway routes, CloudFront, S3.
#
# Usage:
#   chmod +x scripts/setup/step-3c-deploy-backend.sh
#   AWS_PROFILE=journal-dev ./scripts/setup/step-3c-deploy-backend.sh dev
#
# Optional — deploy only a subset:
#   DEPLOY_API=false    AWS_PROFILE=journal-dev ./scripts/setup/step-3c-deploy-backend.sh dev
#   DEPLOY_AI=false     AWS_PROFILE=journal-dev ./scripts/setup/step-3c-deploy-backend.sh dev
#   DEPLOY_SFN=false    AWS_PROFILE=journal-dev ./scripts/setup/step-3c-deploy-backend.sh dev
#
# When API Gateway routes have been added/changed (main.tf api_routes map changed):
#   DEPLOY_ROUTES=true  AWS_PROFILE=journal-dev ./scripts/setup/step-3c-deploy-backend.sh dev

set -euo pipefail

ENV_NAME="${1:-dev}"
TF_DIR="${TF_DIR:-infra/terraform}"
REL_VAR_FILE="environments/${ENV_NAME}/${ENV_NAME}.tfvars"
BACKEND_FILE="${TF_DIR}/backend.${ENV_NAME}.tfbackend"

# Feature flags — set to "false" to skip a component
DEPLOY_API="${DEPLOY_API:-true}"
DEPLOY_AI="${DEPLOY_AI:-true}"
DEPLOY_SFN="${DEPLOY_SFN:-true}"
# Set DEPLOY_ROUTES=true when API Gateway routes have been added/changed (api_routes map in main.tf)
DEPLOY_ROUTES="${DEPLOY_ROUTES:-false}"

echo "== Backend Deploy (Template 3) =="
echo "Environment   : ${ENV_NAME}"
echo "TF_DIR        : ${TF_DIR}"
echo "Deploy API    : ${DEPLOY_API}"
echo "Deploy AI     : ${DEPLOY_AI}"
echo "Deploy SFN    : ${DEPLOY_SFN}"
echo "Deploy Routes : ${DEPLOY_ROUTES}"
echo

# ── Pre-flight ────────────────────────────────────────────────────────────────
if [ ! -d "${TF_DIR}" ]; then
  echo "ERROR: Terraform directory not found: ${TF_DIR}"
  exit 1
fi

if [ ! -f "${TF_DIR}/${REL_VAR_FILE}" ]; then
  echo "ERROR: tfvars not found: ${TF_DIR}/${REL_VAR_FILE}"
  exit 1
fi

if [ ! -f "${BACKEND_FILE}" ]; then
  echo "ERROR: backend config not found: ${BACKEND_FILE}"
  echo "Tip: run step-2-bootstrap-terraform-backend.sh first"
  exit 1
fi

# ── Clear Lambda zip caches ───────────────────────────────────────────────────
# Terraform's archive_file data source caches the zip at the output_path.
# If the cache exists with a matching hash, Terraform won't repackage the source.
# Deleting the cache forces a fresh zip on every run → always picks up code changes.
echo ">> Clearing Lambda zip caches..."
API_ZIP="${TF_DIR}/modules/compute_lambda/.build/api.zip"
AI_ZIP="${TF_DIR}/modules/ai_gateway/.build/ai-gateway.zip"
PRE_SIGNUP_ZIP="${TF_DIR}/modules/auth/lambda/pre_signup.zip"

[ -f "${API_ZIP}"        ] && rm -f "${API_ZIP}"        && echo "   Removed ${API_ZIP}"
[ -f "${AI_ZIP}"         ] && rm -f "${AI_ZIP}"         && echo "   Removed ${AI_ZIP}"
[ -f "${PRE_SIGNUP_ZIP}" ] && rm -f "${PRE_SIGNUP_ZIP}" && echo "   Removed ${PRE_SIGNUP_ZIP}"
echo

# ── Terraform init ────────────────────────────────────────────────────────────
pushd "${TF_DIR}" >/dev/null

echo ">> terraform init"
terraform init -reconfigure -backend-config="$(basename "${BACKEND_FILE}")"
echo

# ── Build targeted apply arguments ───────────────────────────────────────────
TARGETS=()

if [ "${DEPLOY_API}" = "true" ]; then
  TARGETS+=( "-target=module.compute_lambda[0].aws_lambda_function.this" )
fi

if [ "${DEPLOY_AI}" = "true" ]; then
  TARGETS+=( "-target=module.ai_gateway.aws_iam_role_policy.inline" )
  TARGETS+=( "-target=module.ai_gateway.aws_lambda_function.this" )
fi

if [ "${DEPLOY_SFN}" = "true" ]; then
  TARGETS+=( "-target=module.workflow.aws_sfn_state_machine.this" )
fi

if [ "${DEPLOY_ROUTES}" = "true" ]; then
  # Add/update API Gateway routes, integrations, and Lambda permissions
  TARGETS+=( "-target=module.api_edge.aws_apigatewayv2_api.this" )
  TARGETS+=( "-target=module.api_edge.aws_apigatewayv2_route.this" )
  TARGETS+=( "-target=module.api_edge.aws_apigatewayv2_integration.lambda" )
  TARGETS+=( "-target=module.api_edge.aws_lambda_permission.allow_apigw" )
  # Also redeploy API Lambda IAM if permissions changed
  TARGETS+=( "-target=module.compute_lambda[0].aws_iam_role_policy.inline" )
fi

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "Nothing to deploy (all DEPLOY_* flags are false)."
  popd >/dev/null
  exit 0
fi

echo ">> terraform plan (targeted)"
terraform plan -var-file="${REL_VAR_FILE}" "${TARGETS[@]}"

echo
echo ">> terraform apply (targeted)"
terraform apply -var-file="${REL_VAR_FILE}" "${TARGETS[@]}"

popd >/dev/null

echo
echo "✅ Backend deploy complete for env: ${ENV_NAME}"
echo
echo "What was deployed:"
[ "${DEPLOY_API}"    = "true" ] && echo "  ✓ API Lambda           (module.compute_lambda)"
[ "${DEPLOY_AI}"     = "true" ] && echo "  ✓ AI Gateway Lambda    (module.ai_gateway IAM + function)"
[ "${DEPLOY_SFN}"    = "true" ] && echo "  ✓ Step Functions       (module.workflow state machine)"
[ "${DEPLOY_ROUTES}" = "true" ] && echo "  ✓ API Gateway routes   (module.api_edge routes + integrations)"
echo
echo "If you also changed the web frontend, run:"
echo "   AWS_PROFILE=${AWS_PROFILE:-journal-dev} ./scripts/setup/step-4a-deploy-web-to-s3.sh ${ENV_NAME}"
