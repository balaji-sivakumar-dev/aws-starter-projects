#!/usr/bin/env python3
"""
Local test runner for ai_gateway.py

Tests the Groq LLM call directly — no DynamoDB involved.
Useful for verifying your API key and model before deploying to AWS.

Usage:
    # Make sure your venv is active or boto3 is installed
    pip install boto3

    # Set your Groq key and run:
    GROQ_API_KEY=gsk_... python3 scripts/test_ai_gateway_local.py

Optional overrides:
    GROQ_MODEL_ID=llama-3.3-70b-versatile  python3 scripts/test_ai_gateway_local.py
    LLM_PROVIDER=bedrock                    python3 scripts/test_ai_gateway_local.py
"""

import os
import sys

# ── point to the lambda source so we can import it ────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "services", "workflows", "src"))

# ── minimal env vars so ai_gateway.py can be imported ─────────────────────────
os.environ.setdefault("JOURNAL_TABLE_NAME", "local-test-table")  # not used in this test
os.environ.setdefault("LLM_PROVIDER",  "groq")
os.environ.setdefault("GROQ_MODEL_ID", "llama-3.1-8b-instant")

# Check key is set
if os.environ.get("LLM_PROVIDER") == "groq" and not os.environ.get("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY is not set.")
    print("  export GROQ_API_KEY=gsk_...")
    sys.exit(1)

# ── import after env vars are set ─────────────────────────────────────────────
from ai_gateway import call_groq, call_bedrock, invoke_llm, extract_json, normalize_tags

SAMPLE_TITLE = "Productive morning session"
SAMPLE_BODY  = (
    "Woke up at 6am and spent 90 minutes working on the new API design. "
    "Made good progress on the authentication module. Feeling energised. "
    "Need to follow up with the team about the database schema tomorrow."
)

PROMPT = (
    "Return only JSON with keys summary and tags. "
    "summary <= 240 chars, tags 1..5 short lowercase tags.\n"
    f"title: {SAMPLE_TITLE}\n"
    f"body: {SAMPLE_BODY}"
)

print("=" * 60)
print(f"  LLM provider : {os.environ['LLM_PROVIDER']}")
if os.environ["LLM_PROVIDER"] == "groq":
    print(f"  Model        : {os.environ['GROQ_MODEL_ID']}")
print("=" * 60)
print(f"  Title  : {SAMPLE_TITLE}")
print(f"  Body   : {SAMPLE_BODY[:80]}...")
print()

try:
    print(">> Calling LLM...")
    raw_text = invoke_llm(PROMPT)
    print(f"   Raw response : {raw_text[:200]}")
    print()

    parsed = extract_json(raw_text)
    summary = str(parsed.get("summary") or "").strip()[:240]
    tags    = normalize_tags(parsed.get("tags")) or ["journal"]

    print("✅ Success!")
    print(f"   Summary : {summary}")
    print(f"   Tags    : {tags}")

except Exception as exc:
    print(f"❌ Failed: {exc}")
    sys.exit(1)
