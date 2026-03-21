#!/bin/bash
# Local Groq test — invokes ai_gateway.py directly against local DynamoDB.
#
# Setup (one-time):
#   cp .env.local.example .env.local
#   # Edit .env.local and set GROQ_API_KEY
#
# Run:
#   bash scripts/tests/test_groq_local.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"  # scripts/tests/ → scripts/ → repo root

# ── Load secrets from .env.local (gitignored) ─────────────────────────────────
ENV_FILE="$REPO_ROOT/.env.local"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
else
  echo "ERROR: .env.local not found."
  echo "  Run: cp .env.local.example .env.local  then set GROQ_API_KEY inside it."
  exit 1
fi

export LLM_PROVIDER="groq"
export GROQ_MODEL_ID="${GROQ_MODEL_ID:-llama-3.1-8b-instant}"
# ─────────────────────────────────────────────────────────────────────────────

# ── Python venv — create and install deps if missing ─────────────────────────
VENV_DIR="${REPO_ROOT}/services/api/.venv"
PYTHON="${VENV_DIR}/bin/python3"

if [ ! -f "$PYTHON" ]; then
  echo "  Python venv not found — creating it..."
  python3 -m venv "$VENV_DIR"
  echo "  Installing boto3..."
  "${VENV_DIR}/bin/pip" install --quiet boto3
  echo "  ✅ venv ready."
elif ! "$PYTHON" -c "import boto3" 2>/dev/null; then
  echo "  boto3 not found — installing..."
  "${VENV_DIR}/bin/pip" install --quiet boto3
fi

cd "$REPO_ROOT"
"$PYTHON" scripts/tests/test_ai_gateway_local.py
