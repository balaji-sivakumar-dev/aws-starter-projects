#!/usr/bin/env bash
# scripts/config.sh — Single source of truth for deployment constants.
#
# Source this file from every setup/destroy script:
#   source "$(dirname "$0")/../config.sh" "$1"
#
# It sets: APP_PREFIX, ENV, AWS_REGION, SSM_PREFIX, and all SSM parameter paths.
# Override any value via environment variables before sourcing.

set -euo pipefail

# ── Core ──────────────────────────────────────────────────────────────────────
APP_PREFIX="${APP_PREFIX:-{{APP_PREFIX}}}"
ENV="${1:-dev}"
AWS_REGION="${AWS_REGION:-{{AWS_REGION}}}"

# ── SSM Parameter Paths ──────────────────────────────────────────────────────
SSM_PREFIX="/${APP_PREFIX}/${ENV}"
SSM_ALLOWED_EMAILS="${SSM_PREFIX}/cognito/allowed_emails"
SSM_ADMIN_EMAILS="${SSM_PREFIX}/cognito/admin_emails"
SSM_GROQ_KEY="${SSM_PREFIX}/ai/groq_api_key"
SSM_OPENAI_KEY="${SSM_PREFIX}/ai/openai_api_key"

# ── Terraform ─────────────────────────────────────────────────────────────────
TF_DIR="$(cd "$(dirname "$0")/../infra/terraform" && pwd)"
TF_BACKEND_KEY="${APP_PREFIX}/${ENV}/terraform.tfstate"

# ── Computed ──────────────────────────────────────────────────────────────────
TABLE_NAME="${APP_PREFIX}-${ENV}"
STACK_PREFIX="${APP_PREFIX}-${ENV}"

export APP_PREFIX ENV AWS_REGION SSM_PREFIX
export SSM_ALLOWED_EMAILS SSM_ADMIN_EMAILS SSM_GROQ_KEY SSM_OPENAI_KEY
export TF_DIR TF_BACKEND_KEY TABLE_NAME STACK_PREFIX
