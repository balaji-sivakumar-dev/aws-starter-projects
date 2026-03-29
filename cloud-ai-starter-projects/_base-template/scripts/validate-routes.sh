#!/usr/bin/env bash
# scripts/validate-routes.sh — Validate that routes.yaml, Terraform, and handler are in sync.
#
# Usage: bash scripts/validate-routes.sh
#
# Checks:
# 1. Every route in routes.yaml has a matching entry in Terraform api_routes
# 2. Every route in routes.yaml has a handler entry in Lambda handler.py
# 3. Reports mismatches and exits non-zero if any are found

set -euo pipefail

ROUTES_FILE="routes.yaml"
TF_MAIN="infra/terraform/main.tf"
HANDLER="services/lambda_api/src/handler.py"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

if [ ! -f "$ROUTES_FILE" ]; then
  echo -e "${RED}ERROR: $ROUTES_FILE not found${NC}"
  exit 1
fi

ERRORS=0

echo "Validating routes alignment..."
echo ""

# Extract routes from routes.yaml (path + method pairs)
# Simple grep-based parsing (no yq dependency)
ROUTE_PAIRS=""
CURRENT_PATH=""
while IFS= read -r line; do
  # Match "- path: /something"
  if echo "$line" | grep -q "^[[:space:]]*-[[:space:]]*path:"; then
    CURRENT_PATH=$(echo "$line" | sed 's/.*path:[[:space:]]*//' | tr -d '"' | tr -d "'")
  fi
  # Match "method: GET"
  if echo "$line" | grep -q "^[[:space:]]*method:"; then
    METHOD=$(echo "$line" | sed 's/.*method:[[:space:]]*//' | tr -d '"' | tr -d "'" | tr '[:lower:]' '[:upper:]')
    if [ -n "$CURRENT_PATH" ]; then
      ROUTE_PAIRS="$ROUTE_PAIRS
$METHOD $CURRENT_PATH"
    fi
  fi
done < "$ROUTES_FILE"

ROUTE_COUNT=$(echo "$ROUTE_PAIRS" | grep -c '[A-Z]' || true)
echo "Found $ROUTE_COUNT routes in $ROUTES_FILE"

# Check Terraform
if [ -f "$TF_MAIN" ]; then
  echo -n "Checking Terraform ($TF_MAIN)... "
  TF_MISSING=0
  while IFS= read -r pair; do
    [ -z "$pair" ] && continue
    PATH_VAL=$(echo "$pair" | awk '{print $2}')
    # Terraform uses path without leading slash and {param} style
    TF_PATH=$(echo "$PATH_VAL" | sed 's|^/||' | sed 's|{[^}]*}|$|g')
    if ! grep -q "$TF_PATH" "$TF_MAIN" 2>/dev/null; then
      echo ""
      echo -e "  ${YELLOW}WARN: $pair — not found in Terraform${NC}"
      TF_MISSING=$((TF_MISSING + 1))
    fi
  done <<< "$ROUTE_PAIRS"
  if [ "$TF_MISSING" -eq 0 ]; then
    echo -e "${GREEN}OK${NC}"
  else
    echo -e "  ${YELLOW}$TF_MISSING routes missing from Terraform${NC}"
    ERRORS=$((ERRORS + TF_MISSING))
  fi
else
  echo -e "${YELLOW}SKIP: $TF_MAIN not found${NC}"
fi

# Check Lambda handler
if [ -f "$HANDLER" ]; then
  echo -n "Checking Lambda handler ($HANDLER)... "
  HANDLER_MISSING=0
  while IFS= read -r pair; do
    [ -z "$pair" ] && continue
    PATH_VAL=$(echo "$pair" | awk '{print $2}')
    # Handler uses the path directly in quotes
    if ! grep -q "\"$PATH_VAL\"" "$HANDLER" 2>/dev/null; then
      # Try with single quotes or partial match
      SIMPLE_PATH=$(echo "$PATH_VAL" | sed 's|{[^}]*}||g' | sed 's|/$||')
      if ! grep -q "$SIMPLE_PATH" "$HANDLER" 2>/dev/null; then
        echo ""
        echo -e "  ${YELLOW}WARN: $pair — not found in Lambda handler${NC}"
        HANDLER_MISSING=$((HANDLER_MISSING + 1))
      fi
    fi
  done <<< "$ROUTE_PAIRS"
  if [ "$HANDLER_MISSING" -eq 0 ]; then
    echo -e "${GREEN}OK${NC}"
  else
    echo -e "  ${YELLOW}$HANDLER_MISSING routes missing from handler${NC}"
    ERRORS=$((ERRORS + HANDLER_MISSING))
  fi
else
  echo -e "${YELLOW}SKIP: $HANDLER not found${NC}"
fi

echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo -e "${RED}FAIL: $ERRORS route mismatches found${NC}"
  exit 1
else
  echo -e "${GREEN}PASS: All routes aligned${NC}"
fi
