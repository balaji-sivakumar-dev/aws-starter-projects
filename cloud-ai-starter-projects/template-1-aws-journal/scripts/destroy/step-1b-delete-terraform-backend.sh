#!/bin/bash
# Step 1B — Delete backend too (optional “nuke everything”)

set -euo pipefail

# ⚠️ Use this only if you want to delete the state bucket and lock table.
# This will remove your Terraform state history.

# chmod +x scripts/destroy/step-1b-delete-terraform-backend.sh
# AWS_PROFILE=journal-dev ./scripts/destroy/step-1b-delete-terraform-backend.sh


REGION="${REGION:-ca-central-1}"
PROJECT_PREFIX="${PROJECT_PREFIX:-journal}"
LOCK_TABLE="${LOCK_TABLE:-${PROJECT_PREFIX}-tflock}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
STATE_BUCKET="${STATE_BUCKET:-${PROJECT_PREFIX}-tfstate-${ACCOUNT_ID}-${REGION}}"

echo "== Delete Terraform Backend =="
echo "Account     : ${ACCOUNT_ID}"
echo "Region      : ${REGION}"
echo "State bucket: ${STATE_BUCKET}"
echo "Lock table  : ${LOCK_TABLE}"
echo

read -p "Type DELETE to confirm deleting backend resources: " CONFIRM
if [ "${CONFIRM}" != "DELETE" ]; then
  echo "Cancelled."
  exit 0
fi

echo ">> Deleting all objects + versions in S3 bucket (this can take a bit if many versions exist)..."

# Delete all object versions + delete markers
VERSIONS_JSON="$(aws s3api list-object-versions --bucket "${STATE_BUCKET}" --output json)"

# Use python (available on mac) to safely build delete payload in chunks
export STATE_BUCKET
export VERSIONS_JSON
python3 - <<'PY'
import json, sys, subprocess, math, os

bucket = os.environ["STATE_BUCKET"]
data = json.loads(os.environ["VERSIONS_JSON"])

objs = []
for v in data.get("Versions", []):
    objs.append({"Key": v["Key"], "VersionId": v["VersionId"]})
for m in data.get("DeleteMarkers", []):
    objs.append({"Key": m["Key"], "VersionId": m["VersionId"]})

if not objs:
    print("No versions/delete-markers to remove.")
    sys.exit(0)

# S3 delete-objects supports up to 1000 keys per request
chunk = 1000
for i in range(0, len(objs), chunk):
    payload = {"Objects": objs[i:i+chunk], "Quiet": True}
    p = subprocess.run(
        ["aws", "s3api", "delete-objects", "--bucket", bucket, "--delete", json.dumps(payload)],
        capture_output=True, text=True
    )
    if p.returncode != 0:
        print(p.stderr)
        sys.exit(p.returncode)
print(f"Deleted {len(objs)} object versions/delete markers.")
PY

echo ">> Deleting bucket..."
aws s3api delete-bucket --bucket "${STATE_BUCKET}" --region "${REGION}"

echo ">> Deleting DynamoDB lock table..."
aws dynamodb delete-table --table-name "${LOCK_TABLE}" --region "${REGION}"

echo
echo "✅ Backend deleted (state bucket + lock table)."
