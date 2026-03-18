"""
llm_provider.py — Provider-agnostic LLM inference for Lambda RAG /ask

Supports two providers controlled by LLM_PROVIDER env var:

  bedrock (default / recommended)
    Model : BEDROCK_MODEL_ID env var  (default: amazon.nova-lite-v1:0)
    Cost  : ~$0.060/1M input tokens — cheapest option
    Setup : IAM-only, no API key

  openai
    Model : OPENAI_LLM_MODEL env var  (default: gpt-4o-mini)
    Cost  : ~$0.150/1M input tokens — 2.5x more expensive than Nova Lite
    Setup : requires OPENAI_API_KEY env var
    Why   : higher reasoning quality; useful for complex journal analysis

Provider comparison for RAG /ask:
  Nova Lite   → cheapest, good for simple Q&A, ~$0.06/$0.24 per 1M in/out
  gpt-4o-mini → better reasoning, ~$0.15/$0.60 per 1M in/out
  gpt-4o      → best quality, ~$2.50/$10.00 per 1M in/out (not recommended for RAG)

All calls use Python stdlib urllib — no extra packages to bundle in Lambda zip.
boto3 is a Lambda runtime built-in.
"""

import json
import os
import urllib.request

import boto3

# ── Config ────────────────────────────────────────────────────────────────────

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "bedrock").lower().strip()

# Bedrock
_BEDROCK_CLIENT = None
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")

# OpenAI
OPENAI_LLM_MODEL = os.environ.get("OPENAI_LLM_MODEL", "gpt-4o-mini")
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def _bedrock_client():
    global _BEDROCK_CLIENT
    if _BEDROCK_CLIENT is None:
        _BEDROCK_CLIENT = boto3.client(
            "bedrock-runtime",
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )
    return _BEDROCK_CLIENT


# ── Public API ────────────────────────────────────────────────────────────────

def ask(prompt: str, max_tokens: int = 1024) -> str:
    """
    Send a prompt to the configured LLM and return the text response.

    Routes to the configured provider (LLM_PROVIDER env var).
    Raises RuntimeError on failure.
    """
    if LLM_PROVIDER == "openai":
        return _ask_openai(prompt, max_tokens)
    else:
        return _ask_bedrock(prompt, max_tokens)


# ── Bedrock ───────────────────────────────────────────────────────────────────

def _ask_bedrock(prompt: str, max_tokens: int) -> str:
    body = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "inferenceConfig": {"maxTokens": max_tokens},
    })
    try:
        resp = _bedrock_client().invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        result = json.loads(resp["body"].read())
        # Nova / Claude response format
        content = result.get("output", {}).get("message", {}).get("content", [{}])
        return content[0].get("text", "") if content else str(result)
    except Exception as exc:
        raise RuntimeError(f"Bedrock LLM call failed: {exc}") from exc


# ── OpenAI — stdlib urllib, no extra packages ─────────────────────────────────

def _ask_openai(prompt: str, max_tokens: int) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set — cannot use OpenAI LLM provider")

    payload = json.dumps({
        "model": OPENAI_LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENAI_CHAT_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError(f"OpenAI LLM call failed: {exc}") from exc
