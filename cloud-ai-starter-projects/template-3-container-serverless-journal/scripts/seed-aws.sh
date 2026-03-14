#!/bin/bash
# seed-aws.sh
# Seed 20 realistic journal entries into the AWS DynamoDB table.
#
# All AWS config (region, table name) is read automatically from
# Terraform outputs — no manual copy-pasting required.
#
# Usage:
#   AWS_PROFILE=journal-dev ./scripts/seed-aws.sh dev
#   AWS_PROFILE=journal-dev USER_ID=<cognito-sub-uuid> ./scripts/seed-aws.sh dev
#
# USER_ID is the Cognito sub (UUID) for the user you want to seed.
# Find it in:
#   - The app sidebar after login (shown under your email)
#   - AWS Console → Cognito → Users → click your user → "sub" attribute
#   - GET /me endpoint: {"userId": "<sub>", "email": "..."}

set -euo pipefail

ENV="${1:-dev}"
PROFILE="${AWS_PROFILE:-default}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$REPO_ROOT/infra/terraform"
VARS_FILE="$TF_DIR/environments/${ENV}/${ENV}.tfvars"

echo "============================================================"
echo "  Seeding AWS DynamoDB for env : $ENV"
echo "  AWS profile                  : $PROFILE"
echo "============================================================"

# ── Python venv — create and install deps if missing ─────────────────────────
VENV_DIR="$REPO_ROOT/services/api/.venv"
PYTHON="$VENV_DIR/bin/python3"

if [ ! -f "$PYTHON" ]; then
  echo ""
  echo "  Python venv not found — creating it..."
  python3 -m venv "$VENV_DIR"
  echo "  Installing boto3..."
  "$VENV_DIR/bin/pip" install --quiet boto3
  echo "  ✅ venv ready."
elif ! "$PYTHON" -c "import boto3" 2>/dev/null; then
  echo ""
  echo "  boto3 not found in venv — installing..."
  "$VENV_DIR/bin/pip" install --quiet boto3
  echo "  ✅ boto3 installed."
fi

# ── Read config from Terraform outputs ───────────────────────────────────────
echo ""
echo "  Reading Terraform outputs..."
cd "$TF_DIR"

# Init quietly if needed (in case .terraform dir is missing)
if [ ! -d ".terraform" ]; then
  echo "  Running terraform init..."
  terraform init -reconfigure \
    -backend-config="environments/${ENV}/${ENV}.backend" \
    -input=false -no-color > /dev/null 2>&1
fi

# Select / create workspace
terraform workspace select "$ENV" 2>/dev/null || terraform workspace new "$ENV" 2>/dev/null || true

TABLE_NAME=$(terraform output -raw journal_table_name 2>/dev/null)
REGION=$(terraform output -raw region 2>/dev/null)

if [ -z "$TABLE_NAME" ] || [ -z "$REGION" ]; then
  echo ""
  echo "ERROR: Could not read Terraform outputs."
  echo "  Make sure you have run step-3a (terraform apply) first."
  echo "  Expected outputs: journal_table_name, region"
  exit 1
fi

echo "  Table  : $TABLE_NAME"
echo "  Region : $REGION"

# ── Get USER_ID ───────────────────────────────────────────────────────────────
cd "$REPO_ROOT"

if [ -z "${USER_ID:-}" ]; then
  echo ""
  echo "  USER_ID is the Cognito 'sub' (UUID) of the user to seed."
  echo "  Find it: log in to the app → sidebar shows it, or call GET /me"
  echo ""
  echo -n "  Enter USER_ID (Cognito sub UUID): "
  read -r USER_ID
fi

if [ -z "${USER_ID:-}" ]; then
  echo "ERROR: USER_ID is required."
  exit 1
fi

echo "  User   : $USER_ID"
echo ""

# ── Run seed script ───────────────────────────────────────────────────────────
echo "  Seeding entries into DynamoDB (AWS mode)..."
echo "------------------------------------------------------------"

DYNAMODB_ENDPOINT="" \
JOURNAL_TABLE_NAME="$TABLE_NAME" \
USER_ID="$USER_ID" \
AWS_DEFAULT_REGION="$REGION" \
AWS_PROFILE="$PROFILE" \
  "$PYTHON" "$REPO_ROOT/scripts/seed_data.py"

echo "------------------------------------------------------------"
echo ""
echo "  ✅ Done! Open the app to see your journal entries:"

# Print site URL from terraform if available
SITE_URL=$(cd "$TF_DIR" && terraform output -raw site_url 2>/dev/null || echo "")
if [ -n "$SITE_URL" ]; then
  echo "     $SITE_URL"
fi
echo "============================================================"
