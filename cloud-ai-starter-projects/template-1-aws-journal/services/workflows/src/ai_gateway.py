import json
import os
import re
from typing import Any, Dict

import boto3

from workflow_tasks import (
    EntryNotFoundError,
    RateLimitExceededError,
    check_rate_limit,
    get_entry,
    mark_complete,
    mark_failed,
    mark_processing,
)


ddb = boto3.resource("dynamodb")
bedrock = boto3.client("bedrock-runtime")


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    user_id = str(event.get("userId") or "").strip()
    entry_id = str(event.get("entryId") or "").strip()
    request_id = str(event.get("requestId") or "unknown-request-id")

    if not user_id or not entry_id:
        raise ValueError("userId and entryId are required")

    table = ddb.Table(os.environ["JOURNAL_TABLE_NAME"])
    entry = None

    try:
        max_requests = _to_int(os.getenv("AI_RATE_LIMIT_MAX_REQUESTS", "5"), 5)
        window_seconds = _to_int(os.getenv("AI_RATE_LIMIT_WINDOW_SECONDS", "60"), 60)
        check_rate_limit(table, user_id, max_requests=max_requests, window_seconds=window_seconds)

        entry = get_entry(table, user_id, entry_id)
        mark_processing(table, entry)

        max_input_chars = _to_int(os.getenv("MAX_INPUT_CHARS", "8000"), 8000)
        title = str(entry.get("title") or "")
        body = str(entry.get("body") or "")
        if len(body) > max_input_chars:
            raise ValueError(f"entry body exceeds max input size ({max_input_chars})")

        max_output_tokens = _to_int(os.getenv("MAX_OUTPUT_TOKENS", "256"), 256)
        model_id = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
        generated = _generate_summary_and_tags(
            model_id=model_id,
            title=title,
            body=body,
            max_output_tokens=max_output_tokens,
        )

        mark_complete(table, entry, generated["summary"], generated["tags"])

        return {
            "ok": True,
            "userId": user_id,
            "entryId": entry_id,
            "requestId": request_id,
            "summary": generated["summary"],
            "tags": generated["tags"],
            "modelId": model_id,
        }

    except RateLimitExceededError:
        if entry:
            mark_failed(table, entry, "rate limit exceeded")
        raise
    except EntryNotFoundError:
        raise
    except Exception as exc:  # noqa: BLE001
        if entry:
            mark_failed(table, entry, _short_error(str(exc)))
        raise


def _generate_summary_and_tags(model_id: str, title: str, body: str, max_output_tokens: int) -> Dict[str, Any]:
    prompt = (
        "You are a journal assistant. Return ONLY valid minified JSON with keys summary and tags. "
        "summary must be <= 240 chars. tags must be 1-5 short lowercase tags without punctuation."
        f" Journal title: {title}\n"
        f"Journal body: {body}"
    )

    response = bedrock.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ],
        inferenceConfig={
            "maxTokens": max_output_tokens,
            "temperature": 0.2,
        },
    )

    output = response.get("output") or {}
    message = output.get("message") or {}
    content = message.get("content") or []
    text = ""
    if content and isinstance(content, list):
        text = str(content[0].get("text") or "")

    parsed = _extract_json(text)
    summary = _clean_summary(parsed.get("summary"))
    tags = _clean_tags(parsed.get("tags"))

    if not summary:
        raise ValueError("model returned empty summary")
    if not tags:
        tags = ["journal"]

    return {
        "summary": summary,
        "tags": tags,
    }


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("model returned no content")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("model output was not JSON")

    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("model output JSON must be object")
    return parsed


def _clean_summary(value: Any) -> str:
    summary = str(value or "").strip()
    if len(summary) > 240:
        summary = summary[:240].rstrip()
    return summary


def _clean_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    tags: list[str] = []
    for raw in value[:5]:
        tag = re.sub(r"[^a-z0-9- ]", "", str(raw).lower()).strip().replace(" ", "-")
        if tag and tag not in tags:
            tags.append(tag[:24])
    return tags


def _to_int(raw: str, default: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _short_error(message: str) -> str:
    if not message:
        return "unknown error"
    return message[:180]
