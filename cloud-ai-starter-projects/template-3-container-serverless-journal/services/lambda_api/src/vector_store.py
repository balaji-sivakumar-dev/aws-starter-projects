"""
vector_store.py — DynamoDB-backed vector store for RAG

Stores Bedrock Titan embedding vectors alongside journal entries in the
existing DynamoDB table.  No extra infrastructure needed.

DynamoDB key schema for vector items:
  PK  = "USER#<user_id>"
  SK  = "VECTOR#<entry_id>"

Stored fields:
  embedding  — JSON list of 1536 floats (Decimal-free; stored as string)
  entryId    — the journal entry this vector represents
  title      — snippet for result display
  bodySnippet — first 500 chars of entry body
  updatedAt  — ISO timestamp of last embed

Search strategy:
  - Fetch all VECTOR# items for the user (a single DynamoDB Query)
  - Compute cosine similarity in-memory (Python)
  - Works well up to ~1 000 entries; re-evaluate at scale

Security:
  - Never exposed via a direct public endpoint
  - Only called from Lambda handler which requires a valid Cognito JWT
"""

import json
import os

import boto3
from boto3.dynamodb.conditions import Key

TABLE = boto3.resource("dynamodb").Table(os.environ["JOURNAL_TABLE_NAME"])


# ── DynamoDB helpers ──────────────────────────────────────────────────────────

def _pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _sk(entry_id: str) -> str:
    return f"VECTOR#{entry_id}"


# ── Public API ────────────────────────────────────────────────────────────────

def upsert_vector(user_id: str, entry_id: str, embedding: list, title: str, body_snippet: str, updated_at: str) -> None:
    """Store or overwrite the embedding vector for an entry."""
    TABLE.put_item(Item={
        "PK": _pk(user_id),
        "SK": _sk(entry_id),
        "entityType": "ENTRY_VECTOR",
        "entryId": entry_id,
        "embedding": json.dumps(embedding),   # store as JSON string; avoids Decimal
        "title": title[:200],
        "bodySnippet": body_snippet[:500],
        "updatedAt": updated_at,
    })


def list_vectors(user_id: str) -> list:
    """Return all vector items for the user as a list of dicts."""
    result = TABLE.query(
        KeyConditionExpression=Key("PK").eq(_pk(user_id)) & Key("SK").begins_with("VECTOR#"),
    )
    items = []
    for item in result.get("Items", []):
        items.append({
            "entryId": item["entryId"],
            "embedding": json.loads(item["embedding"]),
            "title": item.get("title", ""),
            "bodySnippet": item.get("bodySnippet", ""),
            "updatedAt": item.get("updatedAt", ""),
        })
    return items


def count_vectors(user_id: str) -> int:
    """Return the number of embedded entries for the user."""
    result = TABLE.query(
        KeyConditionExpression=Key("PK").eq(_pk(user_id)) & Key("SK").begins_with("VECTOR#"),
        Select="COUNT",
    )
    return result.get("Count", 0)


def delete_all_vectors(user_id: str) -> int:
    """Delete all vector items for the user. Returns the count deleted."""
    deleted = 0
    last_key = None
    while True:
        params: dict = {
            "KeyConditionExpression": Key("PK").eq(_pk(user_id)) & Key("SK").begins_with("VECTOR#"),
            "ProjectionExpression": "PK, SK",
        }
        if last_key:
            params["ExclusiveStartKey"] = last_key
        result = TABLE.query(**params)
        with TABLE.batch_writer() as batch:
            for item in result.get("Items", []):
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                deleted += 1
        last_key = result.get("LastEvaluatedKey")
        if not last_key:
            break
    return deleted


def search_vectors(user_id: str, query_embedding: list, top_k: int = 5) -> list:
    """
    Return the top-k most similar entries to the query embedding.

    Uses cosine similarity computed in-memory after fetching all vectors.
    Each result: {"entryId", "title", "bodySnippet", "score"}
    """
    vectors = list_vectors(user_id)
    if not vectors:
        return []

    scored = []
    for item in vectors:
        score = _cosine(query_embedding, item["embedding"])
        scored.append({
            "entryId": item["entryId"],
            "title": item["title"],
            "bodySnippet": item["bodySnippet"],
            "score": round(score, 4),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ── Math ──────────────────────────────────────────────────────────────────────

def _cosine(a: list, b: list) -> float:
    """Cosine similarity between two equal-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
