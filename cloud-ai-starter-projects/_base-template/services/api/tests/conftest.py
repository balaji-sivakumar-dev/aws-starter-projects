"""
Pytest fixtures for integration tests.

Uses moto to mock DynamoDB — no running Docker container needed.
The FastAPI TestClient is used for HTTP-level testing.

Environment strategy
--------------------
APP_ENV is set to "test" so the FastAPI lifespan skips _wait_for_dynamo()
and ensure_table() (which target a real endpoint).  The conftest creates
the table directly via moto before each test function.
"""

import os

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

# ── Fake AWS credentials so moto / boto3 don't reach out to AWS ──────────────

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

# Use a dedicated test table name and disable the real DynamoDB endpoint so
# moto can intercept boto3 calls via the standard AWS endpoint.
os.environ["TABLE_NAME"] = "test-table"
os.environ.pop("DYNAMODB_ENDPOINT", None)   # moto handles the endpoint
os.environ["APP_ENV"] = "test"              # skip _wait_for_dynamo / JWKS load


TABLE_NAME = "test-table"


def _create_table(ddb_resource) -> None:
    """Create the app table schema in the mocked DynamoDB."""
    ddb_resource.create_table(
        TableName=TABLE_NAME,
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture()
def client():
    """
    FastAPI TestClient backed by a fresh moto DynamoDB table.

    Each test gets a clean table (function scope) to prevent state leaking
    between tests.
    """
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        _create_table(ddb)

        # Import the app *inside* the mock_aws context so every boto3 call
        # made during the test (including module-level singletons) is mocked.
        from src.adapters.fastapi.app import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
