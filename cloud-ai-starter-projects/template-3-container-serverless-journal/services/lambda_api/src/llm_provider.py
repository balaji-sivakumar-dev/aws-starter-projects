"""
llm_provider.py — Provider-agnostic LLM inference for Lambda RAG /ask

Supports three providers controlled by LLM_PROVIDER env var:

  bedrock (default / recommended for AWS deployments)
    Model : BEDROCK_MODEL_ID env var  (default: amazon.nova-lite-v1:0)
    Region: BEDROCK_REGION env var    (default: us-east-1 — use us-east-1 if ca-central-1 lacks the model)
    Cost  : ~$0.060/1M input tokens
    Setup : IAM-only, no API key

  groq
    Model : GROQ_MODEL_ID env var     (default: llama-3.1-8b-instant)
    Cost  : free tier available
    Setup : GROQ_API_KEY env var (store in SSM, pass via Terraform)

  openai
    Model : OPENAI_LLM_MODEL env var  (default: gpt-4o-mini)
    Cost  : ~$0.150/1M input tokens
    Setup : OPENAI_API_KEY env var
"""

import json
import os
import urllib.request

import boto3

# ── Config ────────────────────────────────────────────────────────────────────

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "bedrock").lower().strip()

# Bedrock — use BEDROCK_REGION so we can cross-region call us-east-1 from ca-central-1
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1"))
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")

# Groq
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL_ID = os.environ.get("GROQ_MODEL_ID", "llama-3.1-8b-instant")

# OpenAI
OPENAI_LLM_MODEL = os.environ.get("OPENAI_LLM_MODEL", "gpt-4o-mini")
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

_BEDROCK_CLIENT = None


def _bedrock_client():
    global _BEDROCK_CLIENT
    if _BEDROCK_CLIENT is None:
        _BEDROCK_CLIENT = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    return _BEDROCK_CLIENT


# ── Public API ────────────────────────────────────────────────────────────────

def ask(prompt: str, max_tokens: int = 1024) -> str:
    """
    Send a prompt to the configured LLM and return the text response.
    Routes to the configured provider (LLM_PROVIDER env var).
    Raises RuntimeError on failure.
    """
    if LLM_PROVIDER == "groq":
        return _ask_groq(prompt, max_tokens)
    if LLM_PROVIDER == "openai":
        return _ask_openai(prompt, max_tokens)
    return _ask_bedrock(prompt, max_tokens)


def provider_name() -> str:
    """Return the active provider name string."""
    return LLM_PROVIDER or "bedrock"


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


# ── Groq ──────────────────────────────────────────────────────────────────────

def _ask_groq(prompt: str, max_tokens: int) -> str:
    import urllib.error
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set — cannot use Groq LLM provider")

    payload = json.dumps({
        "model": GROQ_MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")

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
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Groq API error {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Groq LLM call failed: {exc}") from exc


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
