#!/usr/bin/env bash
# scripts/migrate-to-standalone.sh
#
# Copies _base-template into a new standalone git repo at a target path.
#
# Usage:
#   bash scripts/migrate-to-standalone.sh
#   bash scripts/migrate-to-standalone.sh /custom/path/aws-full-stack-template
#
# Default destination: /Users/balajisivakumar/Storage/dev/personal-repo/cloud-projects/aws-full-stack-template
#
# After running this script:
#   cd <destination>
#   make new-project APP=myapp         # creates ../myapp (sibling to the template repo)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_DEST="/Users/balajisivakumar/Storage/dev/personal-repo/cloud-projects/aws-full-stack-template"
DEST="${1:-$DEFAULT_DEST}"

echo ""
echo "  AWS Full-Stack Template — Migrate to Standalone Repo"
echo "  ─────────────────────────────────────────────────────"
echo "  Source : $BASE_DIR"
echo "  Dest   : $DEST"
echo ""

if [ -d "$DEST" ]; then
  echo "ERROR: $DEST already exists. Remove it first or choose a different path."
  exit 1
fi

# ── Copy template ─────────────────────────────────────────────────────────────
echo "  Copying template files..."
cp -R "$BASE_DIR" "$DEST"

# Remove mono-repo artefacts not needed in standalone repo
rm -f "$DEST/scripts/migrate-to-standalone.sh"   # remove self
rm -rf "$DEST/apps/web/node_modules"              # reinstall fresh
rm -rf "$DEST/services/api/.venv"                 # reinstall fresh

# ── Init git repo ─────────────────────────────────────────────────────────────
echo "  Initialising git repo..."
cd "$DEST"
git init -q
git add .
git commit -q -m "Initial commit — AWS Full-Stack Starter Template"

echo ""
echo "  ✓ Standalone repo created at:"
echo "    $DEST"
echo ""
echo "  Next: create a new app"
echo "    cd $DEST"
echo "    make new-project APP=myapp"
echo "    # → creates $(dirname "$DEST")/myapp"
echo ""
