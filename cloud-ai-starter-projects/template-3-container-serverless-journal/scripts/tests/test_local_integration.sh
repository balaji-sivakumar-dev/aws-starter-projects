#!/usr/bin/env bash
# =============================================================================
# test_local_integration.sh — Integration test suite for the local Docker stack
#
# Lifecycle (fully automated):
#   1. docker compose down       — tear down any running stack
#   2. docker compose up --build — start fresh stack (waits for healthy)
#   3. Seed data                 — load ~195 journal entries
#   4. Run API tests             — entries, RAG embed/search/ask, insights
#   5. docker compose down       — tear down after tests
#
# Usage (from template-3 root):
#   bash scripts/tests/test_local_integration.sh
#
# Options (env vars):
#   API_BASE    override API URL          (default: http://localhost:8080)
#   USER_ID     override user ID header   (default: dev-user)
#   VERBOSE     set to 1 for full bodies  (default: 0)
#   SKIP_DOWN   set to 1 to skip teardown after tests (default: 0)
#
# Examples:
#   cd template-3-container-serverless-journal
#   bash scripts/tests/test_local_integration.sh
#   VERBOSE=1 bash scripts/tests/test_local_integration.sh
#   SKIP_DOWN=1 VERBOSE=1 bash scripts/tests/test_local_integration.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"   # scripts/tests/ → scripts/ → repo root

API_BASE="${API_BASE:-http://localhost:8080}"
USER_ID="${USER_ID:-dev-user}"
VERBOSE="${VERBOSE:-0}"
SKIP_DOWN="${SKIP_DOWN:-0}"
PASS=0
FAIL=0

COMPOSE_CMD="docker compose \
  -f $REPO_ROOT/docker-compose.yml \
  -f $REPO_ROOT/docker-compose.ollama.yml \
  -f $REPO_ROOT/docker-compose.rag.yml"

PYTHON="$REPO_ROOT/services/api/.venv/bin/python3"

# ── Colour helpers ────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

pass()   { echo -e "${GREEN}✓${NC} $1"; PASS=$((PASS + 1)); }
fail()   { echo -e "${RED}✗${NC} $1"; FAIL=$((FAIL + 1)); }
info()   { echo -e "${YELLOW}→${NC} $1"; }
header() { echo; echo -e "${BLUE}═══ $1 ═══${NC}"; }

# ── API call helper ───────────────────────────────────────────────────────────

api() {
  local method="$1"; local path="$2"; shift 2
  curl -s -X "$method" "$API_BASE$path" \
    -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    "$@"
}

# ── Assertions ────────────────────────────────────────────────────────────────

assert_field() {
  local label="$1"; local json="$2"; local field="$3"; local expected="$4"
  local actual
  actual=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "PARSE_ERROR")
  if [[ "$actual" == "$expected" ]]; then
    pass "$label"
  else
    fail "$label (expected '$expected', got '$actual')"
    [[ "$VERBOSE" == "1" ]] && echo "  Response: $json"
  fi
}

assert_contains() {
  local label="$1"; local json="$2"; local key="$3"
  if echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$key' in d" 2>/dev/null; then
    pass "$label"
  else
    fail "$label (key '$key' missing from response)"
    [[ "$VERBOSE" == "1" ]] && echo "  Response: $json"
  fi
}

assert_gt() {
  local label="$1"; local json="$2"; local field="$3"; local min="$4"
  local actual
  actual=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "0")
  if [[ "$actual" -gt "$min" ]] 2>/dev/null; then
    pass "$label ($actual > $min)"
  else
    fail "$label (expected > $min, got '$actual')"
    [[ "$VERBOSE" == "1" ]] && echo "  Response: $json"
  fi
}

# ── Wait for API to be ready ──────────────────────────────────────────────────

wait_for_api() {
  local retries=30
  local delay=5
  info "Waiting for API to be ready at $API_BASE ..."
  for i in $(seq 1 $retries); do
    if curl -s --max-time 3 "$API_BASE/entries" -H "X-User-Id: $USER_ID" > /dev/null 2>&1; then
      pass "API is ready (attempt $i/$retries)"
      return 0
    fi
    echo "  Attempt $i/$retries — not ready yet, waiting ${delay}s..."
    sleep $delay
  done
  echo -e "${RED}ERROR: API did not become ready after $((retries * delay))s${NC}"
  echo "  Check logs: docker logs t3-api"
  exit 1
}

# ── Teardown on exit (unless SKIP_DOWN=1) ─────────────────────────────────────

teardown() {
  if [[ "$SKIP_DOWN" == "1" ]]; then
    info "SKIP_DOWN=1 — leaving stack running"
    return
  fi
  header "Teardown"
  info "Stopping stack (keeping Ollama model volumes)..."
  cd "$REPO_ROOT"
  $COMPOSE_CMD down
  info "Stack stopped."
}
trap teardown EXIT

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Tear down existing stack
# ═════════════════════════════════════════════════════════════════════════════

header "Phase 1: Tear Down Existing Stack"

cd "$REPO_ROOT"
info "Running docker compose down..."
$COMPOSE_CMD down
pass "Existing stack torn down"

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Start fresh stack
# ═════════════════════════════════════════════════════════════════════════════

header "Phase 2: Start Fresh Stack"

info "Running docker compose up --build -d ..."
info "(First run downloads Ollama models ~2.5 GB — may take several minutes)"
$COMPOSE_CMD up --build -d
pass "docker compose up completed"

# Wait for one-shot model-pull containers to finish
info "Waiting for model pull containers to complete..."
for container in t3-ollama-pull t3-ollama-pull-embed; do
  for i in $(seq 1 60); do
    status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "missing")
    exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$container" 2>/dev/null || echo "?")
    if [[ "$status" == "exited" ]]; then
      if [[ "$exit_code" == "0" ]]; then
        pass "$container: model pulled successfully (Exited 0)"
      else
        fail "$container: model pull failed (Exited $exit_code) — check: docker logs $container"
      fi
      break
    fi
    [[ $i -eq 1 ]] && echo "  Waiting for $container..."
    sleep 5
  done
done

# Wait for API
wait_for_api

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Seed data
# ═════════════════════════════════════════════════════════════════════════════

header "Phase 3: Seed Journal Entries"

if [[ ! -f "$PYTHON" ]]; then
  fail "Python venv not found at $PYTHON — run setup first"
  exit 1
fi

info "Running seed script..."
cd "$REPO_ROOT"
seed_output=$("$PYTHON" scripts/seed_data/seed_data.py 2>&1)
seeded=$(echo "$seed_output" | grep -oE '[0-9]+ entries seeded' | grep -oE '[0-9]+' || echo "0")
if [[ "$seeded" -gt 0 ]]; then
  pass "Seeded $seeded entries"
else
  # Try to detect success even if count extraction failed
  if echo "$seed_output" | grep -qi "done\|seeded\|created"; then
    pass "Seed script completed"
  else
    fail "Seed script may have failed — output: $seed_output"
  fi
fi

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 4 — API Tests
# ═════════════════════════════════════════════════════════════════════════════

# ── Entries CRUD ──────────────────────────────────────────────────────────────

header "Phase 4a: Entries API"

resp=$(api GET "/entries?limit=10")
assert_contains "GET /entries returns items array" "$resp" "items"
entry_count=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['items']))" 2>/dev/null || echo "0")
if [[ "$entry_count" -gt 0 ]]; then
  pass "Seed data present ($entry_count entries in first page)"
else
  fail "No entries found after seeding"
fi

create_resp=$(api POST "/entries" -d '{"title":"Integration Test Entry","body":"This entry was created by the integration test script."}')
assert_contains "POST /entries creates entry" "$create_resp" "item"
ENTRY_ID=$(echo "$create_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['item']['entryId'])" 2>/dev/null || echo "")

if [[ -n "$ENTRY_ID" ]]; then
  pass "Created test entry: $ENTRY_ID"
  get_resp=$(api GET "/entries/$ENTRY_ID")
  assert_field "GET /entries/{id} returns correct title" "$get_resp" "['item']['title']" "Integration Test Entry"
  del_resp=$(api DELETE "/entries/$ENTRY_ID")
  assert_contains "DELETE /entries/{id} succeeds" "$del_resp" "deleted"
else
  fail "Could not parse entry ID from create response"
fi

# ── RAG Embed-All ─────────────────────────────────────────────────────────────

header "Phase 4b: RAG — Embed All Entries"

status_before=$(api GET "/rag/status")
assert_contains "GET /rag/status returns totalVectors" "$status_before" "totalVectors"

info "Running embed-all (~195 entries, may take 2-5 min)..."
embed_resp=$(api POST "/rag/embed-all" --max-time 600)
assert_field "POST /rag/embed-all status is completed" "$embed_resp" "['status']" "completed"
assert_gt   "POST /rag/embed-all embedded > 0 entries"  "$embed_resp" "['embedded']" 0

embedded=$(echo "$embed_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('embedded',0))" 2>/dev/null || echo "0")
failed=$(echo "$embed_resp"   | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('failed',0))"   2>/dev/null || echo "?")
info "Embedded: $embedded  Failed: $failed"

if [[ "$failed" != "0" && "$failed" != "?" ]]; then
  fail "Some entries failed to embed ($failed failures) — check: docker logs t3-api"
fi

status_after=$(api GET "/rag/status")
vectors=$(echo "$status_after" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['totalVectors'])" 2>/dev/null || echo "0")
if [[ "$vectors" -gt 0 ]]; then
  pass "Vector store has $vectors vectors after embed"
else
  fail "Vector count is 0 after embed-all"
fi

# ── RAG Search ────────────────────────────────────────────────────────────────

header "Phase 4c: RAG — Semantic Search"

search_resp=$(api POST "/rag/search" -d '{"query":"hiking with family","top_k":3}')
assert_contains "POST /rag/search returns results" "$search_resp" "results"
result_count=$(echo "$search_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['results']))" 2>/dev/null || echo "0")
if [[ "$result_count" -gt 0 ]]; then
  pass "Search returned $result_count matching entries"
else
  fail "Search returned no results"
fi

# ── RAG Ask ───────────────────────────────────────────────────────────────────

header "Phase 4d: RAG — Ask Journal"

info "Asking journal a question (LLM generation, ~30-60s)..."
ask_resp=$(api POST "/rag/ask" -d '{"query":"What hobbies do I enjoy most?","top_k":5}' --max-time 120)
assert_contains "POST /rag/ask returns answer"  "$ask_resp" "answer"
assert_contains "POST /rag/ask returns sources" "$ask_resp" "sources"

answer=$(echo "$ask_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('answer','')[:80])" 2>/dev/null || echo "")
if [[ -n "$answer" ]] && [[ "$answer" != "null" ]]; then
  pass "Ask returned answer: \"${answer}...\""
else
  fail "Ask returned empty or null answer"
  [[ "$VERBOSE" == "1" ]] && echo "  Response: $ask_resp"
fi

# ── Insights ──────────────────────────────────────────────────────────────────

header "Phase 4e: Insights — Yearly Summary"

list_resp=$(api GET "/insights/summaries")
assert_contains "GET /insights/summaries returns items" "$list_resp" "items"

info "Generating yearly insights for 2025 (LLM, ~50-90s)..."
gen_resp=$(api POST "/insights/summaries" -d '{"period":"yearly","year":2025}' --max-time 150)
assert_contains "POST /insights/summaries returns item" "$gen_resp" "item"

ai_status=$(echo "$gen_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['item'].get('aiStatus',''))" 2>/dev/null || echo "")
if [[ "$ai_status" == "DONE" ]]; then
  pass "Insights generated (aiStatus=DONE)"
elif [[ "$ai_status" == "ERROR" ]]; then
  fail "Insights returned aiStatus=ERROR"
  [[ "$VERBOSE" == "1" ]] && echo "  Response: $gen_resp"
else
  info "aiStatus=$ai_status"
fi

# ═════════════════════════════════════════════════════════════════════════════
# Results
# ═════════════════════════════════════════════════════════════════════════════

echo
echo "══════════════════════════════════════════"
echo -e "  Results: ${GREEN}${PASS} passed${NC}  ${RED}${FAIL} failed${NC}"
echo "══════════════════════════════════════════"

if [[ "$FAIL" -gt 0 ]]; then
  echo "  VERBOSE=1 bash scripts/tests/test_local_integration.sh   — see full responses"
  echo "  docker logs t3-api --tail 50                              — see API errors"
  exit 1
fi
