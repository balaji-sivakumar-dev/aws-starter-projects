#!/usr/bin/env bash
# scripts/new-project.sh — Bootstrap a new project from the base template.
#
# Usage:
#   bash scripts/new-project.sh budget
#   bash scripts/new-project.sh budget --defaults    # skip interactive prompts
#
# Creates: cloud-ai-starter-projects/template-{APP_PREFIX}/
#
# The script:
# 1. Reads template.json for variable prompts (or uses --defaults)
# 2. Copies _base-template/ → template-{APP_PREFIX}/
# 3. Replaces all {{PLACEHOLDER}} strings with actual values
# 4. Removes opt-out features (dirs/files listed in template.json)
# 5. Generates .env files with correct values
# 6. Runs npm install in apps/web/
# 7. Prints next steps

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BASE_DIR="$REPO_ROOT/cloud-ai-starter-projects/_base-template"
PROJECTS_DIR="$REPO_ROOT/cloud-ai-starter-projects"

# ── Parse arguments ──────────────────────────────────────────────────────────

APP_PREFIX="${1:-}"
USE_DEFAULTS=false

if [ -z "$APP_PREFIX" ]; then
  echo "Usage: $0 <app-name> [--defaults]"
  echo "  e.g.: $0 budget"
  exit 1
fi

shift
while [ $# -gt 0 ]; do
  case "$1" in
    --defaults) USE_DEFAULTS=true ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# Validate APP_PREFIX
if ! echo "$APP_PREFIX" | grep -qE '^[a-z][a-z0-9-]{1,20}$'; then
  echo "ERROR: APP_PREFIX must be lowercase letters, numbers, hyphens. 2-21 chars. Got: $APP_PREFIX"
  exit 1
fi

TARGET_DIR="$PROJECTS_DIR/template-$APP_PREFIX"

if [ -d "$TARGET_DIR" ]; then
  echo "ERROR: $TARGET_DIR already exists. Remove it first or choose a different name."
  exit 1
fi

if [ ! -d "$BASE_DIR" ]; then
  echo "ERROR: Base template not found at $BASE_DIR"
  exit 1
fi

# ── Collect variables ────────────────────────────────────────────────────────

prompt_var() {
  local var_name="$1"
  local prompt_text="$2"
  local default="$3"

  if [ "$USE_DEFAULTS" = true ]; then
    echo "$default"
    return
  fi

  read -rp "  $prompt_text [$default]: " value
  echo "${value:-$default}"
}

echo ""
echo "  Creating new project: template-$APP_PREFIX"
echo "  ────────────────────────────────────────────"
echo ""

APP_TITLE=$(prompt_var "APP_TITLE" "Display name" "$(echo "$APP_PREFIX" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')")
AWS_REGION=$(prompt_var "AWS_REGION" "AWS region" "ca-central-1")
AWS_PROFILE=$(prompt_var "AWS_PROFILE" "AWS CLI profile" "$APP_PREFIX-dev")
ENABLE_AI=$(prompt_var "ENABLE_AI" "Enable AI enrichment? (y/n)" "y")
ENABLE_RAG=$(prompt_var "ENABLE_RAG" "Enable RAG / Ask? (y/n)" "y")
ENABLE_ADMIN=$(prompt_var "ENABLE_ADMIN" "Enable admin dashboard? (y/n)" "y")
ENABLE_CSV_IMPORT=$(prompt_var "ENABLE_CSV_IMPORT" "Enable CSV import? (y/n)" "y")
ENABLE_INSIGHTS=$(prompt_var "ENABLE_INSIGHTS" "Enable period insights? (y/n)" "y")

echo ""
echo "  Configuration:"
echo "    APP_PREFIX     = $APP_PREFIX"
echo "    APP_TITLE      = $APP_TITLE"
echo "    AWS_REGION     = $AWS_REGION"
echo "    AWS_PROFILE    = $AWS_PROFILE"
echo "    ENABLE_AI      = $ENABLE_AI"
echo "    ENABLE_RAG     = $ENABLE_RAG"
echo "    ENABLE_ADMIN   = $ENABLE_ADMIN"
echo "    ENABLE_CSV     = $ENABLE_CSV_IMPORT"
echo "    ENABLE_INSIGHTS= $ENABLE_INSIGHTS"
echo ""

if [ "$USE_DEFAULTS" != true ]; then
  read -rp "  Proceed? (y/n) [y]: " confirm
  if [ "${confirm:-y}" != "y" ]; then
    echo "Cancelled."
    exit 0
  fi
fi

# ── Copy template ────────────────────────────────────────────────────────────

echo ""
echo "  Copying base template..."
cp -R "$BASE_DIR" "$TARGET_DIR"

# Remove template metadata from the new project
rm -f "$TARGET_DIR/template.json"
rm -f "$TARGET_DIR/scripts/new-project.sh"

# ── Replace placeholders ─────────────────────────────────────────────────────

echo "  Replacing placeholders..."

# Use find + sed (macOS-compatible)
find "$TARGET_DIR" -type f \( \
  -name "*.py" -o -name "*.tf" -o -name "*.sh" -o -name "*.yml" -o \
  -name "*.yaml" -o -name "*.json" -o -name "*.jsx" -o -name "*.js" -o \
  -name "*.html" -o -name "*.md" -o -name "*.css" -o -name "*.example" -o \
  -name "Makefile" -o -name "Dockerfile" -o -name ".gitignore" \
\) -exec sed -i '' \
  -e "s|{{APP_PREFIX}}|$APP_PREFIX|g" \
  -e "s|{{APP_TITLE}}|$APP_TITLE|g" \
  -e "s|{{AWS_REGION}}|$AWS_REGION|g" \
  -e "s|{{AWS_PROFILE}}|$AWS_PROFILE|g" \
  {} +

# ── Remove opt-out features ──────────────────────────────────────────────────

remove_feature() {
  local feature_name="$1"
  echo "  Removing opt-out feature: $feature_name"

  case "$feature_name" in
    ai)
      rm -rf "$TARGET_DIR/services/workflows"
      rm -f "$TARGET_DIR/apps/web/src/components/ProviderSelector.jsx"
      rm -f "$TARGET_DIR/apps/web/src/state/useProvider.js"
      rm -f "$TARGET_DIR/apps/web/src/api/config.js"
      rm -f "$TARGET_DIR/docker/docker-compose.groq.yml"
      rm -f "$TARGET_DIR/docker/docker-compose.openai.yml"
      rm -f "$TARGET_DIR/docker/docker-compose.ollama.yml"
      ;;
    rag)
      rm -rf "$TARGET_DIR/services/api/src/rag"
      rm -f "$TARGET_DIR/services/api/src/adapters/fastapi/rag_routes.py"
      rm -f "$TARGET_DIR/services/lambda_api/src/embeddings.py"
      rm -f "$TARGET_DIR/services/lambda_api/src/vector_store.py"
      rm -f "$TARGET_DIR/services/lambda_api/src/llm_provider.py"
      rm -f "$TARGET_DIR/apps/web/src/components/AskPanel.jsx"
      rm -f "$TARGET_DIR/apps/web/src/api/rag.js"
      rm -f "$TARGET_DIR/docker/docker-compose.rag.yml"
      ;;
    admin)
      rm -f "$TARGET_DIR/services/api/src/adapters/fastapi/admin_routes.py"
      rm -f "$TARGET_DIR/services/api/src/core/audit.py"
      rm -f "$TARGET_DIR/apps/web/src/components/AdminPanel.jsx"
      rm -f "$TARGET_DIR/apps/web/src/api/admin.js"
      ;;
    csv_import)
      rm -f "$TARGET_DIR/apps/web/src/components/ImportCSV.jsx"
      ;;
    insights)
      rm -f "$TARGET_DIR/services/api/src/adapters/fastapi/insights_routes.py"
      rm -f "$TARGET_DIR/services/api/src/core/insights.py"
      rm -f "$TARGET_DIR/apps/web/src/components/InsightsPanel.jsx"
      rm -f "$TARGET_DIR/apps/web/src/api/insights.js"
      rm -f "$TARGET_DIR/apps/web/src/state/useInsights.js"
      ;;
  esac
}

[ "$ENABLE_AI" != "y" ] && remove_feature "ai"
[ "$ENABLE_RAG" != "y" ] && remove_feature "rag"
[ "$ENABLE_ADMIN" != "y" ] && remove_feature "admin"
[ "$ENABLE_CSV_IMPORT" != "y" ] && remove_feature "csv_import"
[ "$ENABLE_INSIGHTS" != "y" ] && remove_feature "insights"

# ── Generate .env files ──────────────────────────────────────────────────────

echo "  Generating .env files..."

cat > "$TARGET_DIR/.env.docker" << ENVEOF
# Docker Compose environment — loaded automatically
COMPOSE_PROJECT_NAME=$APP_PREFIX
TABLE_NAME=$APP_PREFIX
APP_TITLE=$APP_TITLE
ENVEOF

cat > "$TARGET_DIR/.env.users" << ENVEOF
# Cognito user allowlist — one email per line
# Lines starting with "admin:" designate admins
# Run 'make secrets' after editing
admin:you@example.com
ENVEOF

# ── Create IMPLEMENTATION_CHECKLIST.md ────────────────────────────────────────

cat > "$TARGET_DIR/docs/IMPLEMENTATION_CHECKLIST.md" << MDEOF
# Implementation Checklist — $APP_TITLE

## Requirements

| ID | Requirement | Status | Notes |
|----|------------|--------|-------|
| R-001 | Project bootstrap from base template | Done | Generated by new-project.sh |

## Issues

| ID | Issue | Status | Notes |
|----|-------|--------|-------|

## Fixes

| ID | Fix | Status | Notes |
|----|-----|--------|-------|
MDEOF

# ── Install npm dependencies ─────────────────────────────────────────────────

if command -v npm &> /dev/null; then
  echo "  Installing web dependencies..."
  (cd "$TARGET_DIR/apps/web" && npm install --silent 2>/dev/null) || echo "  WARN: npm install failed — run manually: cd $TARGET_DIR/apps/web && npm install"
else
  echo "  SKIP: npm not found — run: cd $TARGET_DIR/apps/web && npm install"
fi

# ── Remove test files that reference template-specific code ─────────────────

echo "  Cleaning up template-specific test files..."
rm -rf "$TARGET_DIR/services/api/tests/test_bedrock_rag.py"
rm -rf "$TARGET_DIR/services/api/tests/test_rag_conversations.py"
rm -rf "$TARGET_DIR/services/api/tests/test_rag_embedding.py"
rm -rf "$TARGET_DIR/scripts/seed_data"
rm -rf "$TARGET_DIR/scripts/tests"
rm -rf "$TARGET_DIR/docs/Reflect APP AWS.drawio.xml"
rm -rf "$TARGET_DIR/docs/openapi.yaml"
rm -rf "$TARGET_DIR/docs/openapi.html"
rm -rf "$TARGET_DIR/docs/AWS-Console-Setup.md"
rm -rf "$TARGET_DIR/docs/AWS-Cost-Estimate.md"
rm -rf "$TARGET_DIR/docs/RAG-Implementation-Checklist.md"
rm -rf "$TARGET_DIR/docs/Testing-Local.md"

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Project created: template-$APP_PREFIX/"
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Next steps:"
echo ""
echo "  1. cd $TARGET_DIR"
echo "  2. make dev                    # local dev stack"
echo "  3. Edit services/api/src/core/ # add your domain models"
echo ""
echo "  For AWS deployment:"
echo "  4. cp .env.users.example .env.users  # add your emails"
echo "  5. make bootstrap              # Terraform backend"
echo "  6. make secrets                # SSM parameters"
echo "  7. make infra                  # Terraform apply"
echo "  8. make deploy                 # Deploy everything"
echo "  9. make cognito-admin          # Create admin user"
echo ""
