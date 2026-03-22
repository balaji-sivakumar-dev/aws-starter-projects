"""
Vector store interface and implementations.

All vector stores implement the VectorStore ABC. Each user's embeddings
are isolated by tenant_id (user_id) to prevent cross-user data leakage.

VECTOR_STORE values:
  chroma    →  ChromaDB          (local Docker container for development)
  dynamodb  →  DynamoDBVectorStore  (AWS Lambda / serverless — no extra server)

Usage:
    from src.rag.store_factory import get_vector_store
    store = get_vector_store()
    store.upsert(tenant_id="user1", doc_id="entry-123", vector=[0.1, ...], metadata={...}, text="...")
    results = store.search(tenant_id="user1", query_vector=[0.1, ...], top_k=5)
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from the vector store."""
    doc_id: str
    score: float
    text: str
    metadata: dict = field(default_factory=dict)


class VectorStore(ABC):
    """Abstract base class for all vector stores."""

    @abstractmethod
    def upsert(self, tenant_id: str, doc_id: str, vector: list[float],
               metadata: dict, text: str) -> None:
        """Insert or update a document embedding."""

    @abstractmethod
    def search(self, tenant_id: str, query_vector: list[float],
               top_k: int = 5) -> list[SearchResult]:
        """Search for similar documents, scoped to a tenant."""

    @abstractmethod
    def delete(self, tenant_id: str, doc_id: str) -> None:
        """Delete a document embedding."""

    @abstractmethod
    def count(self, tenant_id: str) -> int:
        """Count total documents for a tenant."""

    @abstractmethod
    def delete_all(self, tenant_id: str) -> None:
        """Delete all documents for a tenant."""


class ChromaDBStore(VectorStore):
    """Vector store backed by ChromaDB (local development)."""

    def __init__(self) -> None:
        import chromadb  # lazy import

        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", "8000"))
        self.client = chromadb.HttpClient(host=host, port=port)
        logger.info("ChromaDBStore initialised (host=%s, port=%d)", host, port)

    def _collection(self, tenant_id: str):
        """Get or create a collection for a tenant."""
        safe_name = f"tenant_{tenant_id.replace('-', '_')[:48]}"
        return self.client.get_or_create_collection(
            name=safe_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, tenant_id: str, doc_id: str, vector: list[float],
               metadata: dict, text: str) -> None:
        collection = self._collection(tenant_id)
        collection.upsert(
            ids=[doc_id],
            embeddings=[vector],
            metadatas=[metadata],
            documents=[text],
        )
        logger.debug("Upserted doc_id=%s for tenant=%s", doc_id, tenant_id)

    def search(self, tenant_id: str, query_vector: list[float],
               top_k: int = 5) -> list[SearchResult]:
        collection = self._collection(tenant_id)
        if collection.count() == 0:
            return []
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for i in range(len(results["ids"][0])):
            output.append(SearchResult(
                doc_id=results["ids"][0][i],
                score=1.0 - results["distances"][0][i],  # cosine distance → similarity
                text=results["documents"][0][i],
                metadata=results["metadatas"][0][i],
            ))
        return output

    def delete(self, tenant_id: str, doc_id: str) -> None:
        collection = self._collection(tenant_id)
        collection.delete(ids=[doc_id])
        logger.debug("Deleted doc_id=%s for tenant=%s", doc_id, tenant_id)

    def count(self, tenant_id: str) -> int:
        collection = self._collection(tenant_id)
        return collection.count()

    def delete_all(self, tenant_id: str) -> None:
        safe_name = f"tenant_{tenant_id.replace('-', '_')[:48]}"
        try:
            self.client.delete_collection(name=safe_name)
            logger.info("Deleted all vectors for tenant=%s", tenant_id)
        except Exception:
            logger.debug("No collection to delete for tenant=%s", tenant_id)


class DynamoDBVectorStore(VectorStore):
    """Vector store backed by DynamoDB using the existing single-table design.

    Items stored with:
      PK = 'VEC#<tenant_id>'  (never collides with 'USER#' items)
      SK = 'DOC#<doc_id>'

    Cosine similarity is computed in Lambda memory after querying all tenant
    vectors.  Suitable for personal data (< 5 000 items per user).

    Required env var: TABLE_NAME
    IAM: dynamodb:PutItem, dynamodb:DeleteItem, dynamodb:Query on the table
         (already granted to the API Lambda by Terraform).
    """

    def __init__(self) -> None:
        import boto3  # lazy import

        self.table_name = os.getenv("TABLE_NAME", "")
        if not self.table_name:
            raise ValueError("TABLE_NAME is required for DynamoDB vector store")

        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table(self.table_name)
        logger.info("DynamoDBVectorStore initialised (table=%s)", self.table_name)

    def _pk(self, tenant_id: str) -> str:
        return f"VEC#{tenant_id}"

    def _sk(self, doc_id: str) -> str:
        return f"DOC#{doc_id}"

    def upsert(self, tenant_id: str, doc_id: str, vector: list[float],
               metadata: dict, text: str) -> None:
        from decimal import Decimal

        # DynamoDB does not accept Python float — store as Decimal
        self.table.put_item(Item={
            "PK": self._pk(tenant_id),
            "SK": self._sk(doc_id),
            "vector": [Decimal(str(v)) for v in vector],
            "text": text,
            "metadata": metadata,
            "docId": doc_id,
        })
        logger.debug("Upserted doc_id=%s for tenant=%s", doc_id, tenant_id)

    def search(self, tenant_id: str, query_vector: list[float],
               top_k: int = 5) -> list[SearchResult]:
        import math
        from boto3.dynamodb.conditions import Key

        # Fetch all vectors for this tenant
        response = self.table.query(
            KeyConditionExpression=Key("PK").eq(self._pk(tenant_id))
        )
        items: list = list(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(self._pk(tenant_id)),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        if not items:
            return []

        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0.0 or norm_b == 0.0:
                return 0.0
            return dot / (norm_a * norm_b)

        scored: list[SearchResult] = []
        for item in items:
            stored = [float(v) for v in item.get("vector", [])]
            if len(stored) != len(query_vector):
                continue
            scored.append(SearchResult(
                doc_id=item.get("docId", ""),
                score=cosine(query_vector, stored),
                text=item.get("text", ""),
                metadata=dict(item.get("metadata", {})),
            ))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def delete(self, tenant_id: str, doc_id: str) -> None:
        self.table.delete_item(Key={
            "PK": self._pk(tenant_id),
            "SK": self._sk(doc_id),
        })
        logger.debug("Deleted doc_id=%s for tenant=%s", doc_id, tenant_id)

    def count(self, tenant_id: str) -> int:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            KeyConditionExpression=Key("PK").eq(self._pk(tenant_id)),
            Select="COUNT",
        )
        total = response.get("Count", 0)
        while "LastEvaluatedKey" in response:
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(self._pk(tenant_id)),
                Select="COUNT",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            total += response.get("Count", 0)
        return total

    def delete_all(self, tenant_id: str) -> None:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            KeyConditionExpression=Key("PK").eq(self._pk(tenant_id)),
            ProjectionExpression="PK, SK",
        )
        items: list = list(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(self._pk(tenant_id)),
                ProjectionExpression="PK, SK",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        for item in items:
            self.table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
        logger.info("Deleted all vectors for tenant=%s (%d items)", tenant_id, len(items))
