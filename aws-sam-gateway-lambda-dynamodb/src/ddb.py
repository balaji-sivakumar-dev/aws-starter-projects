import os
import boto3

_TABLE = None

def table():
    global _TABLE
    if _TABLE is None:
        endpoint = os.getenv("DDB_ENDPOINT", "").strip() or None
        ddb = boto3.resource("dynamodb", endpoint_url=endpoint)
        _TABLE = ddb.Table(os.environ["TABLE_NAME"])
    return _TABLE
