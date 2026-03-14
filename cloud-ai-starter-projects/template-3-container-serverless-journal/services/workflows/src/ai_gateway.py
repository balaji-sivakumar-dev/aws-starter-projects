import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict

import boto3

TABLE = boto3.resource("dynamodb").Table(os.environ["JOURNAL_TABLE_NAME"])

LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "groq")       # "groq" | "bedrock"
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_ID   = os.getenv("GROQ_MODEL_ID", "llama-3.1-8b-instant")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
MAX_INPUT_CHARS  = int(os.getenv("MAX_INPUT_CHARS", "8000"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "256"))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def lookup_sk(entry_id: str) -> str:
    return f"ENTRYID#{entry_id}"


def get_entry(user_id: str, entry_id: str):
    lookup = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": lookup_sk(entry_id)}).get("Item")
    if not lookup:
        raise ValueError("entry not found")
    entry = TABLE.get_item(Key={"PK": user_pk(user_id), "SK": lookup["entrySk"]}).get("Item")
    if not entry or entry.get("deletedAt"):
        raise ValueError("entry not found")
    return entry


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


def call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")

    payload = json.dumps({
        "model": GROQ_MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0.2,
    }).encode()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=25) as resp:
        body = json.loads(resp.read())

    return body["choices"][0]["message"]["content"]


def call_bedrock(prompt: str) -> str:
    bedrock = boto3.client("bedrock-runtime")
    resp = bedrock.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": MAX_OUTPUT_TOKENS, "temperature": 0.2},
    )
    return str((((resp.get("output") or {}).get("message") or {}).get("content") or [{}])[0].get("text") or "")


def invoke_llm(prompt: str) -> str:
    if LLM_PROVIDER == "groq":
        return call_groq(prompt)
    if LLM_PROVIDER == "bedrock":
        return call_bedrock(prompt)
    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}. Must be 'groq' or 'bedrock'.")


def handler(event, _context):
    user_id = str(event.get("userId") or "").strip()
    entry_id = str(event.get("entryId") or "").strip()
    if not user_id or not entry_id:
        raise ValueError("userId and entryId are required")

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

        text = invoke_llm(prompt)
        parsed = extract_json(text)

        summary = str(parsed.get("summary") or "").strip()[:240]
        if not summary:
            raise ValueError("empty summary from model")
        tags = normalize_tags(parsed.get("tags")) or ["journal"]

        TABLE.update_item(
            Key={"PK": entry["PK"], "SK": entry["SK"]},
            UpdateExpression=(
                "SET aiStatus = :s, summary = :summary, tags = :tags, "
                "aiUpdatedAt = :aiUpdatedAt, aiError = :e, updatedAt = :u"
            ),
            ExpressionAttributeValues={
                ":s": "COMPLETE",
                ":summary": summary,
                ":tags": tags,
                ":aiUpdatedAt": now_iso(),
                ":e": None,
                ":u": now_iso(),
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
