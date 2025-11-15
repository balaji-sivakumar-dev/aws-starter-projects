import os
import time
import uuid
import boto3

LOCAL_ENDPOINT = os.getenv("DDB_ENDPOINT", "http://localhost:8000")
TABLE_NAME = os.getenv("TABLE_NAME", "local-todos")
REGION = os.getenv("AWS_REGION", "ca-central-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "dummy")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "dummy")

client = boto3.client(
    "dynamodb",
    endpoint_url=LOCAL_ENDPOINT,
    region_name=REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
resource = boto3.resource(
    "dynamodb",
    endpoint_url=LOCAL_ENDPOINT,
    region_name=REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

def ensure_table():
    existing = client.list_tables().get("TableNames", [])
    if TABLE_NAME not in existing:
        client.create_table(
            TableName=TABLE_NAME,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[{
                "IndexName": "status-index",
                "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 1, "WriteCapacityUnits": 1}
            }],
        )
        print("Creating table...")
        waiter = client.get_waiter('table_exists')
        waiter.wait(TableName=TABLE_NAME)
        time.sleep(1)
    print(f"Table ready: {TABLE_NAME}")

def seed_items():
    tbl = resource.Table(TABLE_NAME)
    for i in range(3):
        item = {
            "id": str(uuid.uuid4()),
            "title": f"Sample Todo {i+1}",
            "description": "From seed script",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        tbl.put_item(Item=item)
    print("Seeded 3 items.")

if __name__ == "__main__":
    ensure_table()
    seed_items()
