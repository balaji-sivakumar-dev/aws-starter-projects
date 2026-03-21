#!/usr/bin/env bash
# =============================================================================
# step-2c-create-cognito-admin.sh
# Create Cognito admin user(s) and store their sub UUIDs in SSM.
#
# Run AFTER step-3a-terraform-apply.sh (needs the Cognito User Pool to exist).
#
# What this script does:
#   1. Reads admin email(s) from .env.users (role=admin entries)
#   2. Creates each admin user in Cognito (suppresses email — sets temp password)
#   3. Extracts the user's Cognito sub (UUID)
#   4. Stores comma-separated sub UUIDs in SSM at:
#        /journal/<env>/admin_user_ids
#   5. Prints the first-login temporary password for each admin
#
# After running this script, re-run step-3c-deploy-backend.sh (targeted apply)
# so the Lambda picks up the updated ADMIN_EMAILS env var from Terraform.
# (ADMIN_EMAILS is already set from step-2b — no extra Terraform change needed.)
#
# Usage:
#   AWS_PROFILE=journal-dev ./scripts/setup/step-2c-create-cognito-admin.sh dev
#
# Options (env vars):
#   AWS_PROFILE    AWS CLI profile  (default: default)
#   TEMP_PASSWORD  Override the generated temp password
# =============================================================================

set -euo pipefail

ENV="${1:-dev}"
PROFILE="${AWS_PROFILE:-default}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
USERS_FILE="$REPO_ROOT/.env.users"

echo "============================================================"
echo "  Creating Cognito admin user(s) for env : $ENV"
echo "  AWS profile                             : $PROFILE"
echo "  Users file                              : $USERS_FILE"
echo "============================================================"

# ── Validate .env.users ───────────────────────────────────────────────────────

if [[ ! -f "$USERS_FILE" ]]; then
  echo "  ERROR: $USERS_FILE not found."
  echo "  Copy the example and add your admin email:"
  echo "    cp .env.users.example .env.users"
  exit 1
fi

# ── Read User Pool ID from Terraform output ───────────────────────────────────

cd "$REPO_ROOT/infra/terraform"
USER_POOL_ID=$(terraform output -raw user_pool_id 2>/dev/null || echo "")

if [[ -z "$USER_POOL_ID" ]]; then
  echo ""
  echo "  ERROR: Could not read user_pool_id from Terraform output."
  echo "  Run step-3a-terraform-apply.sh first, then re-run this script."
  exit 1
fi

echo "  User Pool ID: $USER_POOL_ID"
echo ""

# ── Parse admin emails ────────────────────────────────────────────────────────

ADMIN_EMAILS=()
while IFS='=' read -r email role; do
  [[ -z "$email" || "$email" == \#* ]] && continue
  email="$(echo "$email" | xargs | tr '[:upper:]' '[:lower:]')"
  role="$(echo "$role" | xargs)"
  [[ "$role" == "admin" ]] && ADMIN_EMAILS+=("$email")
done < "$USERS_FILE"

if [[ ${#ADMIN_EMAILS[@]} -eq 0 ]]; then
  echo "  ERROR: No admin users found in $USERS_FILE"
  echo "  Add at least one line like: you@example.com=admin"
  exit 1
fi

# ── Create each admin user and collect sub UUIDs ──────────────────────────────

ADMIN_SUBS=()

for ADMIN_EMAIL in "${ADMIN_EMAILS[@]}"; do
  echo "── $ADMIN_EMAIL ─────────────────────────────────────────────"

  # Generate a secure temporary password if not overridden
  TEMP_PASS="${TEMP_PASSWORD:-Reflect-$(openssl rand -hex 8)!}"

  # Create user (SUPPRESS = no email sent; we print the password below)
  aws cognito-idp admin-create-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$ADMIN_EMAIL" \
    --user-attributes \
      "Name=email,Value=$ADMIN_EMAIL" \
      "Name=email_verified,Value=true" \
      "Name=given_name,Value=Admin" \
    --temporary-password "$TEMP_PASS" \
    --message-action SUPPRESS \
    --profile "$PROFILE" \
    --output text > /dev/null 2>&1 \
  || echo "  (User already exists — skipping creation)"

  # Get the Cognito sub UUID
  SUB=$(aws cognito-idp admin-get-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$ADMIN_EMAIL" \
    --query 'UserAttributes[?Name==`sub`].Value' \
    --output text \
    --profile "$PROFILE" 2>/dev/null || echo "")

  if [[ -z "$SUB" ]]; then
    echo "  ERROR: Could not retrieve sub for $ADMIN_EMAIL — skipping."
    continue
  fi

  ADMIN_SUBS+=("$SUB")
  echo "  ✅ Created: $ADMIN_EMAIL"
  echo "  Sub UUID : $SUB"
  echo "  Temp pwd : $TEMP_PASS"
  echo "  First login: open the app → Sign in → enter email + temp password above."
  echo "  You will be prompted to set a new permanent password."
  echo ""
done

# ── Store sub UUIDs in SSM ────────────────────────────────────────────────────

if [[ ${#ADMIN_SUBS[@]} -eq 0 ]]; then
  echo "  No admin subs collected — SSM not updated."
  exit 1
fi

SUBS_CSV=$(
  IFS=,
  echo "${ADMIN_SUBS[*]}"
)

aws ssm put-parameter \
  --name "/journal/${ENV}/admin_user_ids" \
  --value "$SUBS_CSV" \
  --type "SecureString" \
  --description "Cognito sub UUIDs for admin users in journal-${ENV}" \
  --overwrite \
  --profile "$PROFILE" \
  --output text > /dev/null

echo "  ✅ Stored in SSM: /journal/${ENV}/admin_user_ids"
echo "  Value: $SUBS_CSV"
echo ""
echo "  Admin access is controlled by ADMIN_EMAILS (set from .env.users via"
echo "  step-2b-store-secrets.sh). No re-deploy needed unless you added NEW admins."
echo ""
echo "  Done."
echo "============================================================"
