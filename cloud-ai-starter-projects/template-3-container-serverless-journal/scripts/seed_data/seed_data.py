"""
Seed script — loads ~195 realistic journal entries into DynamoDB.

Works with both local DynamoDB and real AWS DynamoDB.

Run from the template-3 root directory
(same folder as docker-compose.yml):

    cd cloud-ai-starter-projects/template-3-container-serverless-journal

Usage — Local (docker compose running)
--------------------------------------
    # Make sure the stack is up first
    docker compose up -d

    # Option A — use the venv directly (no activation needed)
    services/api/.venv/bin/python3 scripts/seed_data/seed_data.py

    # Option B — activate the venv first
    source services/api/.venv/bin/activate
    python3 scripts/seed_data/seed_data.py
    deactivate

Usage — Local with custom endpoint
-----------------------------------
    DYNAMODB_ENDPOINT=http://localhost:8000 \
      services/api/.venv/bin/python3 scripts/seed_data/seed_data.py

Usage — AWS (uses your default AWS profile / env credentials)
-------------------------------------------------------------
    DYNAMODB_ENDPOINT="" AWS_DEFAULT_REGION=ca-central-1 \
      services/api/.venv/bin/python3 scripts/seed_data/seed_data.py

Usage — Custom user or table
-----------------------------
    USER_ID=alice JOURNAL_TABLE_NAME=journal-prod \
      services/api/.venv/bin/python3 scripts/seed_data/seed_data.py

Usage — AWS via wrapper script (reads config from Terraform)
------------------------------------------------------------
    AWS_PROFILE=journal-dev ./scripts/seed_data/seed-aws.sh dev

Environment variables
---------------------
DYNAMODB_ENDPOINT   DynamoDB endpoint URL. Defaults to http://localhost:8000 for local.
                    Set to "" or unset to use real AWS.
JOURNAL_TABLE_NAME  Table name (default: journal)
USER_ID             Owner of all seeded entries (default: dev-user)
AWS_DEFAULT_REGION  AWS region (default: us-east-1)
"""

import os
import sys
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# ── Config ────────────────────────────────────────────────────────────────────

ENDPOINT = os.getenv("DYNAMODB_ENDPOINT", "http://localhost:8000")
TABLE_NAME = os.getenv("JOURNAL_TABLE_NAME", "journal")
USER_ID = os.getenv("USER_ID", "dev-user")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# ── Seed data ─────────────────────────────────────────────────────────────────
# Imported from entries.py — ~200 entries spanning Apr 2024 – Mar 2026.
# Covers: work/engineering, family, travel, health/fitness, hobbies, cooking,
# friendships, holidays, personal growth, finances, home improvement.

# Allow importing entries.py from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from entries import ENTRIES  # noqa: E402



# ── DynamoDB helpers ──────────────────────────────────────────────────────────

def _build_resource():
    kwargs = {
        "region_name": REGION,
        "config": Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 2}),
    }
    if ENDPOINT:
        kwargs["endpoint_url"] = ENDPOINT
        # Local mode — mocked credentials so boto3 doesn't complain
        kwargs.setdefault("aws_access_key_id", "local")
        kwargs.setdefault("aws_secret_access_key", "local")
    return boto3.resource("dynamodb", **kwargs)


def _ensure_table(ddb):
    """Create table if missing (local only — AWS tables should be pre-provisioned)."""
    try:
        ddb.create_table(
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
        print(f"  Created table '{TABLE_NAME}'.")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceInUseException":
            print(f"  Table '{TABLE_NAME}' already exists — OK.")
        else:
            raise


def _put_entry(table, entry_id: str, ts: str, title: str, body: str):
    pk = f"USER#{USER_ID}"
    sk = f"ENTRY#{ts}#{entry_id}"

    # Main item
    table.put_item(Item={
        "PK": pk,
        "SK": sk,
        "entityType": "JOURNAL_ENTRY",
        "entryId": entry_id,
        "userId": USER_ID,
        "title": title,
        "body": body,
        "createdAt": ts,
        "updatedAt": ts,
        "aiStatus": "NOT_REQUESTED",
        "tags": [],
    })

    # Lookup item (needed by resolve_entry / get_entry)
    table.put_item(Item={
        "PK": pk,
        "SK": f"ENTRYID#{entry_id}",
        "entityType": "ENTRY_LOOKUP",
        "entryId": entry_id,
        "entrySk": sk,
        "createdAt": ts,
    })


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    mode = f"local ({ENDPOINT})" if ENDPOINT else f"AWS ({REGION})"
    print(f"\nSeed target : {mode}")
    print(f"Table       : {TABLE_NAME}")
    print(f"User        : {USER_ID}")
    print(f"Entries     : {len(ENTRIES)}\n")

    ddb = _build_resource()

    if ENDPOINT:
        print("Local mode — ensuring table exists...")
        _ensure_table(ddb)

    table = ddb.Table(TABLE_NAME)

    for i, e in enumerate(ENTRIES, 1):
        entry_id = str(uuid.uuid4())
        _put_entry(table, entry_id, e["ts"], e["title"], e["body"])
        date_part = e["ts"][:10]
        print(f"  [{i:02d}/{len(ENTRIES)}] {date_part}  {e['title']}")

    total = len(ENTRIES)
    print(f"\nDone — {total} entries seeded for user '{USER_ID}'.")
    print("Run 'docker compose up' then visit http://localhost:3000 to see them.")
    print("Generate AI insights via: POST /insights/summaries\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)
