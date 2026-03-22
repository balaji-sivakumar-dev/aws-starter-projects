#!/bin/bash
# Step 1C — Delete the Terraform backend (S3 state bucket + DynamoDB lock table)
#
# ⚠️ Run this ONLY after terraform destroy (step-1a) has completed.
# ⚠️ This permanently deletes your Terraform state history.
# ⚠️ Only use this if you want to tear down everything (nuke all).
#
# Usage:
#   chmod +x scripts/destroy/step-1c-delete-terraform-backend.sh
#   AWS_PROFILE={{APP_PREFIX}}-dev ./scripts/destroy/step-1c-delete-terraform-backend.sh

set -euo pipefail

REGION="${REGION:-us-east-1}"
PROJECT_PREFIX="${PROJECT_PREFIX:-{{APP_PREFIX}}}"
LOCK_TABLE="${LOCK_TABLE:-${PROJECT_PREFIX}-tflock}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
STATE_BUCKET="${STATE_BUCKET:-${PROJECT_PREFIX}-tfstate-${ACCOUNT_ID}-${REGION}}"

echo "== Delete Terraform Backend (Template 3) =="
echo "Account     : ${ACCOUNT_ID}"
echo "Region      : ${REGION}"
echo "State bucket: ${STATE_BUCKET}"
echo "Lock table  : ${LOCK_TABLE}"
echo

read -rp "Type DELETE to confirm deleting the Terraform backend (state + lock table): " CONFIRM
if [ "${CONFIRM}" != "DELETE" ]; then
  echo "Cancelled."
  exit 0
fi

# ── Delete all object versions in the S3 bucket ───────────────────────────────
echo ">> Listing all object versions in S3 bucket..."
VERSIONS_JSON="$(aws s3api list-object-versions \
  --bucket "${STATE_BUCKET}" \
  --output json 2>/dev/null || echo '{"Versions":[],"DeleteMarkers":[]}')"

export STATE_BUCKET VERSIONS_JSON
python3 - <<'PY'
import json, sys, subprocess, os

bucket = os.environ["STATE_BUCKET"]
data = json.loads(os.environ["VERSIONS_JSON"])

objs = []
for v in data.get("Versions", []):
    objs.append({"Key": v["Key"], "VersionId": v["VersionId"]})
for m in data.get("DeleteMarkers", []):
    objs.append({"Key": m["Key"], "VersionId": m["VersionId"]})

if not objs:
    print("No object versions to remove.")
    sys.exit(0)

chunk = 1000
for i in range(0, len(objs), chunk):
    payload = {"Objects": objs[i:i+chunk], "Quiet": True}
    p = subprocess.run(
        ["aws", "s3api", "delete-objects", "--bucket", bucket,
         "--delete", json.dumps(payload)],
        capture_output=True, text=True
    )
    if p.returncode != 0:
        print(p.stderr)
        sys.exit(p.returncode)

print(f"Deleted {len(objs)} object version(s) / delete marker(s).")
PY

echo ">> Deleting S3 bucket: ${STATE_BUCKET}"
aws s3api delete-bucket --bucket "${STATE_BUCKET}" --region "${REGION}"

echo ">> Deleting DynamoDB lock table: ${LOCK_TABLE}"
aws dynamodb delete-table --table-name "${LOCK_TABLE}" --region "${REGION}" >/dev/null

echo
echo "✅ Terraform backend deleted (state bucket + lock table)."
