#!/usr/bin/env bash
set -euo pipefail

# Cleanup helper for SAM deployments:
# - Optionally delete a CloudFormation stack (and wait).
# - Empty a *versioned* S3 bucket (all versions + delete markers) and delete the bucket.
# - Optionally find & delete the SAM helper stack’s artifact bucket.
#
# Requires: awscli, jq

usage() {
  cat <<'USAGE'
Usage:
  cleanup_sam.sh [--region <aws-region>] [--profile <aws-profile>]
                 [--stack <stack-name>]
                 [--bucket <artifact-bucket-name>]
                 [--delete-stack]
                 [--delete-bucket]
                 [--delete-helper-stack] [--helper-stack-name <name>]

Examples:
  # 1) Delete your app stack only
  ./scripts/cleanup_sam.sh --stack sam-todo-stack --delete-stack --region ca-central-1

  # 2) Empty & delete a specific versioned bucket
  ./scripts/cleanup_sam.sh --bucket aws-sam-cli-managed-default-samclisourcebucket-abc123 \
                           --delete-bucket --region ca-central-1

  # 3) Delete app stack, then remove the SAM helper stack AND its artifact bucket
  ./scripts/cleanup_sam.sh --stack sam-todo-stack --delete-stack \
                           --delete-helper-stack --helper-stack-name aws-sam-cli-managed-default \
                           --region ca-central-1

Notes:
  - --profile is optional if you already have a default profile set.
  - If you use --delete-helper-stack, the script will:
      a) discover the helper stack's artifact bucket from its outputs
      b) empty + delete the bucket
      c) delete the helper stack
USAGE
}

REGION="${REGION:-}"
PROFILE="${PROFILE:-}"
STACK_NAME=""
BUCKET_NAME=""
DO_DELETE_STACK="false"
DO_DELETE_BUCKET="false"
DO_DELETE_HELPER="false"
HELPER_STACK_NAME="aws-sam-cli-managed-default"

# ---- parse args ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="$2"; shift 2;;
    --profile) PROFILE="$2"; shift 2;;
    --stack) STACK_NAME="$2"; shift 2;;
    --bucket) BUCKET_NAME="$2"; shift 2;;
    --delete-stack) DO_DELETE_STACK="true"; shift 1;;
    --delete-bucket) DO_DELETE_BUCKET="true"; shift 1;;
    --delete-helper-stack) DO_DELETE_HELPER="true"; shift 1;;
    --helper-stack-name) HELPER_STACK_NAME="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

# ---- prerequisites ----
command -v aws >/dev/null 2>&1 || { echo "aws CLI is required"; exit 1; }
command -v jq  >/dev/null 2>&1 || { echo "jq is required"; exit 1; }

AWS_ARGS=()
[[ -n "$REGION"  ]] && AWS_ARGS+=(--region "$REGION")
[[ -n "$PROFILE" ]] && AWS_ARGS+=(--profile "$PROFILE")

# ---- helpers ----
empty_versioned_bucket() {
  local bucket="$1"
  echo ">> Emptying versioned S3 bucket: $bucket"

  # Delete object versions in batches
  while true; do
    VERS_JSON=$(aws s3api list-object-versions --bucket "$bucket" "${AWS_ARGS[@]}" --output json || true)
    COUNT=$(echo "$VERS_JSON" | jq '[.Versions[]?, .DeleteMarkers[]?] | length')
    if [[ "$COUNT" -eq 0 ]]; then
      echo "   Bucket $bucket is now empty (no versions/delete markers)."
      break
    fi

    # Build a delete manifest (max 1000 at a time is fine)
    DEL_FILE=$(mktemp)
    echo "$VERS_JSON" | jq '{
      Objects: ([.Versions[]? , .DeleteMarkers[]?] | map({Key:.Key, VersionId:.VersionId})),
      Quiet: true
    }' > "$DEL_FILE"

    aws s3api delete-objects --bucket "$bucket" --delete "file://$DEL_FILE" "${AWS_ARGS[@]}" >/dev/null || true
    rm -f "$DEL_FILE"
  done
}

delete_bucket() {
  local bucket="$1"
  empty_versioned_bucket "$bucket"
  echo ">> Deleting bucket: $bucket"
  aws s3api delete-bucket --bucket "$bucket" "${AWS_ARGS[@]}"
}

discover_helper_bucket() {
  local helper_stack="$1"
  echo ">> Discovering artifact bucket from helper stack: $helper_stack"
  OUT=$(aws cloudformation describe-stacks --stack-name "$helper_stack" "${AWS_ARGS[@]}" --output json || true)
  if [[ -z "$OUT" ]]; then
    echo "   Could not describe stack $helper_stack (maybe it doesn't exist?)"
    return 1
  fi

  # Try to pick any Output that looks like a bucket name
  BUCKET=$(echo "$OUT" | jq -r '.Stacks[0].Outputs[]? | select((.OutputKey|test("Bucket|Artifact|SourceBucket"; "i")) or (.OutputValue|test("^[a-z0-9.-]+$"))) | .OutputValue' | head -n1)
  if [[ -z "$BUCKET" || "$BUCKET" == "null" ]]; then
    echo "   Could not find bucket in helper stack outputs. Please pass --bucket explicitly."
    return 1
  fi
  echo "$BUCKET"
}

wait_for_stack_deleted() {
  local stack="$1"
  echo ">> Waiting for stack DELETE_COMPLETE: $stack"
  aws cloudformation wait stack-delete-complete --stack-name "$stack" "${AWS_ARGS[@]}" || true
}

# ---- actions ----
if [[ "$DO_DELETE_STACK" == "true" && -n "$STACK_NAME" ]]; then
  echo ">> Deleting stack: $STACK_NAME"
  aws cloudformation delete-stack --stack-name "$STACK_NAME" "${AWS_ARGS[@]}"
  wait_for_stack_deleted "$STACK_NAME"
fi

if [[ "$DO_DELETE_BUCKET" == "true" && -n "$BUCKET_NAME" ]]; then
  delete_bucket "$BUCKET_NAME"
fi

if [[ "$DO_DELETE_HELPER" == "true" ]]; then
  echo ">> Cleaning up helper stack: $HELPER_STACK_NAME"
  # 1) Find helper bucket
  if [[ -z "$BUCKET_NAME" ]]; then
    set +e
    HELPER_BUCKET=$(discover_helper_bucket "$HELPER_STACK_NAME")
    STATUS=$?
    set -e
    if [[ $STATUS -ne 0 ]]; then
      echo "   Could not auto-discover helper bucket. Pass --bucket <name> if you want it deleted."
    else
      BUCKET_NAME="$HELPER_BUCKET"
    fi
  fi
  # 2) Delete helper bucket if we have it
  if [[ -n "${BUCKET_NAME:-}" ]]; then
    delete_bucket "$BUCKET_NAME"
  fi
  # 3) Delete helper stack
  echo ">> Deleting helper stack: $HELPER_STACK_NAME"
  aws cloudformation delete-stack --stack-name "$HELPER_STACK_NAME" "${AWS_ARGS[@]}" || true
  wait_for_stack_deleted "$HELPER_STACK_NAME"
fi

echo "✅ Done."
