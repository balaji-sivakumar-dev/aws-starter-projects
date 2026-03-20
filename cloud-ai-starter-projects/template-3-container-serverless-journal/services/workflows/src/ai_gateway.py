import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from boto3.dynamodb.conditions import Key

TABLE = boto3.resource("dynamodb").Table(os.environ["JOURNAL_TABLE_NAME"])

LLM_PROVIDER      = os.getenv("LLM_PROVIDER", "groq")        # "groq" | "bedrock"
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_ID     = os.getenv("GROQ_MODEL_ID", "llama-3.1-8b-instant")
BEDROCK_MODEL_ID  = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
MAX_INPUT_CHARS   = int(os.getenv("MAX_INPUT_CHARS", "8000"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "256"))
MAX_SUMMARY_TOKENS = int(os.getenv("MAX_SUMMARY_TOKENS", "512"))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def lookup_sk(entry_id: str) -> str:
    return f"ENTRYID#{entry_id}"


def summary_sk(summary_id: str) -> str:
    return f"SUMMARY#{summary_id}"


def get_entry(user_id: str, entry_id: str):
    lookup = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": lookup_sk(entry_id)}).get("Item")
    if not lookup:
        raise ValueError("entry not found")
    entry = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": lookup["entrySk"]}).get("Item")
    if not entry or entry.get("deletedAt"):
        raise ValueError("entry not found")
    return entry


def get_summary(user_id: str, summary_id: str):
    item = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": summary_sk(summary_id)}).get("Item")
    if not item:
        raise ValueError("summary not found")
    return item


def get_entries_in_range(user_id: str, start_date: str, end_date: str) -> list:
    result = TABLE.query(
        KeyConditionExpression=Key("PK").eq(user_pk(user_id))
        & Key("SK").between(f"ENTRY#{start_date}", f"ENTRY#{end_date}T99"),
    )
    return [i for i in result.get("Items", []) if not i.get("deletedAt")]


def friendly_error(err: Exception) -> str:
    from botocore.exceptions import ClientError
    if isinstance(err, ClientError):
        code = err.response.get("Error", {}).get("Code", "")
        if code == "ValidationException":
            return "AI model not available in this region. Check Bedrock model access in your AWS console."
        if code == "AccessDeniedException":
            return "AI model access denied. Enable model access in the AWS Bedrock console."
        if code == "ResourceNotFoundException":
            return "AI model not found. Verify the model ID is correct."
        if code == "ThrottlingException":
            return "AI model rate limit reached. Please try again later."
        return f"AI processing failed ({code}). Please try again."
    return str(err)[:180]


def extract_json(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty model response")
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if not match:
        raise ValueError("model output not JSON")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("model output JSON must be object")
    return parsed


def normalize_tags(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for raw in values[:5]:
        tag = re.sub(r"[^a-z0-9\s-]", "", str(raw).lower()).strip().replace(" ", "-")
        if tag and tag not in out:
            out.append(tag[:24])
    return out


def call_groq(prompt: str, max_tokens: int) -> str:
    import urllib.error
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")

    payload = json.dumps({
        "model": GROQ_MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }).encode()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "reflect-journal/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise ValueError(f"Groq API error {e.code}: {detail}") from e

    return body["choices"][0]["message"]["content"]


def call_bedrock(prompt: str, max_tokens: int) -> str:
    bedrock = boto3.client("bedrock-runtime")
    resp = bedrock.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2},
    )
    return str((((resp.get("output") or {}).get("message") or {}).get("content") or [{}])[0].get("text") or "")


def invoke_llm(prompt: str, max_tokens: int, provider: str = None) -> str:
    """Call the LLM. `provider` overrides the LLM_PROVIDER env var for this request."""
    p = (provider or LLM_PROVIDER or "groq").lower().strip()
    if p == "groq":
        return call_groq(prompt, max_tokens)
    if p == "bedrock":
        return call_bedrock(prompt, max_tokens)
    raise ValueError(f"Unknown provider: {p!r}. Must be 'groq' or 'bedrock'.")


# ── Entry enrichment ──────────────────────────────────────────────────────────

def enrich_entry(user_id: str, entry_id: str, provider_override: str = None) -> dict:
    entry = get_entry(user_id, entry_id)

    TABLE.update_item(
        Key={"PK": entry["PK"], "SK": entry["SK"]},
        UpdateExpression="SET aiStatus = :s, aiError = :e, updatedAt = :u",
        ExpressionAttributeValues={":s": "PROCESSING", ":e": None, ":u": now_iso()},
    )

    try:
        body = str(entry.get("body") or "")
        if len(body) > MAX_INPUT_CHARS:
            raise ValueError("entry body exceeds configured size")

        prompt = (
            "Return only JSON with keys summary and tags. "
            "summary <= 240 chars, tags 1..5 short lowercase tags.\n"
            f"title: {entry.get('title','')}\n"
            f"body: {body}"
        )

        effective_provider = (provider_override or LLM_PROVIDER or "groq").lower().strip()
        text = invoke_llm(prompt, MAX_OUTPUT_TOKENS, provider=effective_provider)
        parsed = extract_json(text)

        summary = str(parsed.get("summary") or "").strip()[:240]
        if not summary:
            raise ValueError("empty summary from model")
        tags = normalize_tags(parsed.get("tags")) or ["journal"]

        TABLE.update_item(
            Key={"PK": entry["PK"], "SK": entry["SK"]},
            UpdateExpression=(
                "SET aiStatus = :s, summary = :summary, tags = :tags, "
                "aiUpdatedAt = :aiUpdatedAt, aiError = :e, updatedAt = :u, aiProvider = :p"
            ),
            ExpressionAttributeValues={
                ":s": "COMPLETE",
                ":summary": summary,
                ":tags": tags,
                ":aiUpdatedAt": now_iso(),
                ":e": None,
                ":u": now_iso(),
                ":p": effective_provider,
            },
        )

        return {"ok": True, "entryId": entry_id, "userId": user_id, "summary": summary, "tags": tags}

    except Exception as exc:
        TABLE.update_item(
            Key={"PK": entry["PK"], "SK": entry["SK"]},
            UpdateExpression="SET aiStatus = :s, aiError = :e, updatedAt = :u",
            ExpressionAttributeValues={":s": "FAILED", ":e": friendly_error(exc), ":u": now_iso()},
        )
        raise


# ── Period summary generation ─────────────────────────────────────────────────

def generate_summary(user_id: str, summary_id: str, provider_override: str = None) -> dict:
    summary = get_summary(user_id, summary_id)

    TABLE.update_item(
        Key={"PK": summary["PK"], "SK": summary["SK"]},
        UpdateExpression="SET aiStatus = :s, aiError = :e, updatedAt = :u",
        ExpressionAttributeValues={":s": "PROCESSING", ":e": None, ":u": now_iso()},
    )

    try:
        entries = get_entries_in_range(user_id, summary["startDate"], summary["endDate"])
        if not entries:
            raise ValueError("no journal entries found in this period")

        # Build entries text, cap at 30 entries and MAX_INPUT_CHARS
        entries_text = "\n\n".join(
            f"[{e.get('createdAt', '')[:10]}] {e.get('title', '')}\n{str(e.get('body', ''))}"
            for e in entries[:30]
        )
        if len(entries_text) > MAX_INPUT_CHARS:
            entries_text = entries_text[:MAX_INPUT_CHARS]

        period_label = summary.get("periodLabel", "this period")
        prompt = (
            f'Analyse these journal entries from "{period_label}" and return only JSON with:\n'
            '"narrative": 1-2 sentence overview of the period,\n'
            '"themes": list of 2-4 short recurring theme strings,\n'
            '"mood": exactly one of: positive / reflective / challenging / mixed / neutral,\n'
            '"highlights": list of 1-3 key moments or achievements as short strings,\n'
            '"reflection": one sentence insight or takeaway.\n'
            f"\nEntries:\n{entries_text}"
        )

        effective_provider = (provider_override or LLM_PROVIDER or "groq").lower().strip()
        text = invoke_llm(prompt, MAX_SUMMARY_TOKENS, provider=effective_provider)
        parsed = extract_json(text)

        narrative = str(parsed.get("narrative") or "").strip()[:500]
        if not narrative:
            raise ValueError("empty narrative from model")

        themes = [str(t).strip()[:50] for t in (parsed.get("themes") or []) if str(t).strip()][:5]
        mood = str(parsed.get("mood") or "neutral").strip()[:30]
        highlights = [str(h).strip()[:150] for h in (parsed.get("highlights") or []) if str(h).strip()][:5]
        reflection = str(parsed.get("reflection") or "").strip()[:300]

        TABLE.update_item(
            Key={"PK": summary["PK"], "SK": summary["SK"]},
            UpdateExpression=(
                "SET aiStatus = :s, narrative = :n, themes = :t, mood = :m, "
                "highlights = :h, #rf = :r, aiError = :e, updatedAt = :u, aiProvider = :p"
            ),
            ExpressionAttributeNames={"#rf": "reflection"},
            ExpressionAttributeValues={
                ":s": "COMPLETE",
                ":n": narrative,
                ":t": themes,
                ":m": mood,
                ":h": highlights,
                ":r": reflection,
                ":e": None,
                ":u": now_iso(),
                ":p": effective_provider,
            },
        )

        return {"ok": True, "summaryId": summary_id, "userId": user_id}

    except Exception as exc:
        TABLE.update_item(
            Key={"PK": summary["PK"], "SK": summary["SK"]},
            UpdateExpression="SET aiStatus = :s, aiError = :e, updatedAt = :u",
            ExpressionAttributeValues={":s": "FAILED", ":e": friendly_error(exc), ":u": now_iso()},
        )
        raise


# ── Lambda entrypoint ─────────────────────────────────────────────────────────

def handler(event, _context):
    event_type = str(event.get("type") or "entry").strip()
    # providerOverride is set when the user selects a specific provider in the UI
    provider_override = str(event.get("providerOverride") or "").strip().lower() or None

    if event_type == "summary":
        user_id = str(event.get("userId") or "").strip()
        summary_id = str(event.get("summaryId") or "").strip()
        if not user_id or not summary_id:
            raise ValueError("userId and summaryId are required for type=summary")
        return generate_summary(user_id, summary_id, provider_override=provider_override)

    # default: entry enrichment
    user_id = str(event.get("userId") or "").strip()
    entry_id = str(event.get("entryId") or "").strip()
    if not user_id or not entry_id:
        raise ValueError("userId and entryId are required")
    return enrich_entry(user_id, entry_id, provider_override=provider_override)
