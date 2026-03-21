"""
Unit tests — BedrockProvider and DynamoDBVectorStore.

Strategy
--------
- BedrockProvider: botocore Stubber intercepts boto3 API calls (no real AWS).
- DynamoDBVectorStore: moto spins up an in-process DynamoDB (no real AWS).
"""

import json
import os

import boto3
import pytest
from botocore.stub import Stubber
from moto import mock_aws

# ── Helpers ───────────────────────────────────────────────────────────────────

TABLE_NAME = "test-journal"


def _make_table():
    """Create the DynamoDB table in moto's in-process mock."""
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


# ═════════════════════════════════════════════════════════════════════════════
# BedrockProvider
# ═════════════════════════════════════════════════════════════════════════════


class TestBedrockProvider:
    """Tests for BedrockProvider using botocore Stubber."""

    @pytest.fixture(autouse=True)
    def _set_model(self):
        os.environ["BEDROCK_MODEL_ID"] = "amazon.nova-lite-v1:0"
        yield
        os.environ.pop("BEDROCK_MODEL_ID", None)

    def _provider(self):
        from src.llm.providers.bedrock_provider import BedrockProvider
        return BedrockProvider()

    def _stub_converse(self, provider, response_text: str, max_tokens: int = 512):
        """Return a Stubber pre-loaded with one converse response."""
        stubber = Stubber(provider.client)
        stubber.add_response(
            "converse",
            {
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [{"text": response_text}],
                    }
                },
                "stopReason": "end_turn",
                "usage": {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
                "metrics": {"latencyMs": 100},
            },
        )
        return stubber

    def test_enrich_returns_summary_and_tags(self):
        provider = self._provider()
        payload = json.dumps({"summary": "A beautiful hike.", "tags": ["hiking", "nature"]})
        with self._stub_converse(provider, payload):
            result = provider.enrich("Mountain Hike", "Climbed to the summit today.")
        assert result["summary"] == "A beautiful hike."
        assert "hiking" in result["tags"]

    def test_enrich_handles_malformed_json_gracefully(self):
        provider = self._provider()
        with self._stub_converse(provider, "Not valid JSON at all"):
            result = provider.enrich("Bad day", "Terrible.")
        # Falls back to raw text as summary, empty tags
        assert isinstance(result["summary"], str)
        assert result["tags"] == []

    def test_analyze_period_returns_narrative(self):
        provider = self._provider()
        payload = json.dumps({
            "narrative": "A productive month.",
            "themes": ["growth", "work"],
            "mood": "positive",
            "highlights": ["Big project launch"],
            "reflection": "What went well?",
        })
        entries = [{"title": "Work", "body": "Hard day", "createdAt": "2026-01-15"}]
        with self._stub_converse(provider, payload, max_tokens=1024):
            result = provider.analyze_period(entries, "January 2026")
        assert result["narrative"] == "A productive month."
        assert "growth" in result["themes"]
        assert result["mood"] == "positive"

    def test_analyze_period_handles_empty_entries(self):
        provider = self._provider()
        payload = json.dumps({
            "narrative": "No entries.",
            "themes": [],
            "mood": "neutral",
            "highlights": [],
            "reflection": "",
        })
        with self._stub_converse(provider, payload, max_tokens=1024):
            result = provider.analyze_period([], "Empty Month 2026")
        assert result["narrative"] == "No entries."

    def test_default_model_is_nova_lite(self):
        os.environ.pop("BEDROCK_MODEL_ID", None)
        provider = self._provider()
        assert provider.model == "amazon.nova-lite-v1:0"

    def test_custom_model_from_env(self):
        os.environ["BEDROCK_MODEL_ID"] = "anthropic.claude-3-haiku-20240307-v1:0"
        provider = self._provider()
        assert provider.model == "anthropic.claude-3-haiku-20240307-v1:0"


# ═════════════════════════════════════════════════════════════════════════════
# DynamoDBVectorStore
# ═════════════════════════════════════════════════════════════════════════════


class TestDynamoDBVectorStore:
    """Tests for DynamoDBVectorStore using moto in-process DynamoDB."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        # mock_aws must be started before boto3 clients are created
        from moto import mock_aws as _mock_aws
        with _mock_aws():
            os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
            os.environ["AWS_ACCESS_KEY_ID"] = "test"
            os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
            os.environ["JOURNAL_TABLE_NAME"] = TABLE_NAME

            _make_table()

            from src.rag.store_factory import reset_vector_store
            reset_vector_store()
            yield
            reset_vector_store()

    def _store(self):
        from src.rag.store import DynamoDBVectorStore
        return DynamoDBVectorStore()

    # ── upsert / count ────────────────────────────────────────────────────────

    def test_upsert_and_count(self):
        store = self._store()
        store.upsert("user1", "doc1", [0.1, 0.2, 0.3], {"title": "T"}, "Some text")
        assert store.count("user1") == 1

    def test_upsert_overwrites_existing(self):
        store = self._store()
        store.upsert("user1", "doc1", [0.1, 0.2, 0.3], {}, "First")
        store.upsert("user1", "doc1", [0.4, 0.5, 0.6], {}, "Updated")
        assert store.count("user1") == 1

    # ── search ────────────────────────────────────────────────────────────────

    def test_search_returns_most_similar_first(self):
        store = self._store()
        store.upsert("user1", "doc1", [1.0, 0.0, 0.0], {}, "First doc")
        store.upsert("user1", "doc2", [0.0, 1.0, 0.0], {}, "Second doc")
        results = store.search("user1", [1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0].doc_id == "doc1"
        assert results[0].score > 0.99

    def test_search_empty_store_returns_empty(self):
        store = self._store()
        assert store.search("user1", [0.1, 0.2, 0.3]) == []

    def test_search_respects_top_k(self):
        store = self._store()
        for i in range(5):
            store.upsert("user1", f"doc{i}", [float(i), 0.0], {}, f"Doc {i}")
        results = store.search("user1", [1.0, 0.0], top_k=2)
        assert len(results) == 2

    # ── delete ────────────────────────────────────────────────────────────────

    def test_delete_removes_one_item(self):
        store = self._store()
        store.upsert("user1", "doc1", [0.1, 0.2], {}, "Text")
        store.upsert("user1", "doc2", [0.3, 0.4], {}, "Other")
        store.delete("user1", "doc1")
        assert store.count("user1") == 1

    def test_delete_all_removes_only_that_tenant(self):
        store = self._store()
        store.upsert("user1", "doc1", [0.1, 0.2], {}, "User 1")
        store.upsert("user1", "doc2", [0.3, 0.4], {}, "User 1 again")
        store.upsert("user2", "doc3", [0.5, 0.6], {}, "User 2")
        store.delete_all("user1")
        assert store.count("user1") == 0
        assert store.count("user2") == 1  # other tenant unaffected

    # ── multi-tenant isolation ────────────────────────────────────────────────

    def test_search_is_scoped_to_tenant(self):
        store = self._store()
        store.upsert("user1", "doc1", [1.0, 0.0], {}, "User 1 doc")
        store.upsert("user2", "doc2", [0.0, 1.0], {}, "User 2 doc")

        results_1 = store.search("user1", [1.0, 0.0])
        results_2 = store.search("user2", [1.0, 0.0])

        assert len(results_1) == 1
        assert results_1[0].doc_id == "doc1"
        assert len(results_2) == 1
        assert results_2[0].doc_id == "doc2"

    # ── factory wiring ────────────────────────────────────────────────────────

    def test_store_factory_returns_dynamodb_store(self):
        os.environ["VECTOR_STORE"] = "dynamodb"
        from src.rag.store_factory import get_vector_store
        from src.rag.store import DynamoDBVectorStore
        store = get_vector_store()
        assert isinstance(store, DynamoDBVectorStore)
        os.environ.pop("VECTOR_STORE", None)
