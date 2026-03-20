"""
embeddings.py — Provider-agnostic embedding for Lambda RAG

Supports two providers controlled by EMBEDDING_PROVIDER env var:

  bedrock (default / recommended)
    Model : amazon.titan-embed-text-v2:0
    Cost  : $0.020/1M tokens
    Setup : IAM-only — no API key needed (managed by Terraform)

  openai
    Model : text-embedding-3-small  (same cost, OpenAI-hosted)
    Cost  : $0.020/1M tokens
    Setup : requires OPENAI_API_KEY stored in SSM and passed as env var

Both use Python stdlib only (urllib) for OpenAI — no extra packages to bundle.
boto3 is a Lambda runtime built-in.

Security:
  - Never exposed via a public endpoint
  - All callers require a valid Cognito JWT (API Gateway JWT authorizer)
  - Bedrock: IAM policy on the Lambda execution role
  - OpenAI: API key read from env var (injected from SSM by Terraform)
"""

import json
import os
import urllib.request

import boto3

# ── Config ────────────────────────────────────────────────────────────────────

EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "bedrock").lower().strip()

# Bedrock — use BEDROCK_REGION to allow cross-region calls (e.g. ca-central-1 → us-east-1)
# Titan Text Embeddings v2 is available in us-east-1, us-west-2, eu-west-1 but NOT ca-central-1.
_BEDROCK_CLIENT = None
BEDROCK_EMBED_MODEL = "amazon.titan-embed-text-v2:0"
BEDROCK_DIMENSIONS = 1536
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1"))

# OpenAI
OPENAI_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"


def _bedrock_client():
    global _BEDROCK_CLIENT
    if _BEDROCK_CLIENT is None:
        _BEDROCK_CLIENT = boto3.client(
            "bedrock-runtime",
            region_name=BEDROCK_REGION,
        )
    return _BEDROCK_CLIENT


# ── Public API ────────────────────────────────────────────────────────────────

def embed_text(text: str) -> list:
    """
    Generate an embedding vector for the given text.

    Routes to the configured provider (EMBEDDING_PROVIDER env var).
    Returns a list of floats.
    Raises RuntimeError on failure.
    """
    if not text or not text.strip():
        raise ValueError("text must not be empty")

    if EMBEDDING_PROVIDER == "openai":
        return _embed_openai(text)
    else:
        return _embed_bedrock(text)


# ── Bedrock (Titan Embeddings v2) ─────────────────────────────────────────────

def _embed_bedrock(text: str) -> list:
    body = json.dumps({
        "inputText": text[:25000],
        "dimensions": BEDROCK_DIMENSIONS,
        "normalize": True,
    })
    try:
        resp = _bedrock_client().invoke_model(
            modelId=BEDROCK_EMBED_MODEL,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        return json.loads(resp["body"].read())["embedding"]
    except Exception as exc:
        raise RuntimeError(f"Bedrock embedding failed: {exc}") from exc


# ── OpenAI (text-embedding-3-small) — stdlib urllib, no extra packages ────────

def _embed_openai(text: str) -> list:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set — cannot use OpenAI embedding provider")

    payload = json.dumps({
        "model": OPENAI_EMBED_MODEL,
        "input": text[:25000],
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENAI_EMBED_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["data"][0]["embedding"]
    except Exception as exc:
        raise RuntimeError(f"OpenAI embedding failed: {exc}") from exc
