import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict

import boto3

TABLE = boto3.resource("dynamodb").Table(os.environ["JOURNAL_TABLE_NAME"])
BEDROCK = boto3.client("bedrock-runtime")


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


def short_error(err: Exception) -> str:
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
        max_input_chars = int(os.getenv("MAX_INPUT_CHARS", "8000"))
        max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "256"))
        model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")

        body = str(entry.get("body") or "")
        if len(body) > max_input_chars:
            raise ValueError("entry body exceeds configured size")

        prompt = (
            "Return only JSON with keys summary and tags. "
            "summary <= 240 chars, tags 1..5 short lowercase tags.\n"
            f"title: {entry.get('title','')}\n"
            f"body: {body}"
        )

        resp = BEDROCK.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_output_tokens, "temperature": 0.2},
        )

        text = str((((resp.get("output") or {}).get("message") or {}).get("content") or [{}])[0].get("text") or "")
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
            ExpressionAttributeValues={":s": "FAILED", ":e": short_error(exc), ":u": now_iso()},
        )
        raise
