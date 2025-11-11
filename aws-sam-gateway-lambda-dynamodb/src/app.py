import json
import uuid
from typing import Dict, Any
from models import TodoCreate, TodoUpdate, TodoItem
from ddb import table

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "*",
}

def _response(status: int, body: Dict[str, Any]):
    return {"statusCode": status, "headers": HEADERS, "body": json.dumps(body)}

def handler(event, context):
    path = event.get("resource") or event.get("path", "")
    http_method = event.get("httpMethod", "GET").upper()
    path_params = event.get("pathParameters") or {}

    try:
        if path == "/todos" and http_method == "POST":
            return create_todo(event)
        if path == "/todos" and http_method == "GET":
            return list_todos(event)
        if path == "/todos/{id}" and http_method == "GET":
            return get_todo(path_params.get("id"))
        if path == "/todos/{id}" and http_method == "PUT":
            return update_todo(path_params.get("id"), event)
        if path == "/todos/{id}" and http_method == "DELETE":
            return delete_todo(path_params.get("id"))

        return _response(404, {"message": "Not Found"})
    except Exception as e:
        return _response(500, {"message": "Internal error", "error": str(e)})

def create_todo(event):
    payload = json.loads(event.get("body") or "{}")
    data = TodoCreate(**payload)

    item = TodoItem(
        id=str(uuid.uuid4()),
        title=data.title,
        description=data.description,
        status=data.status,
        created_at=TodoItem.now_iso(),
        updated_at=TodoItem.now_iso(),
    ).model_dump()

    table().put_item(Item=item)
    return _response(201, item)

def list_todos(event):
    resp = table().scan(Limit=100)
    items = resp.get("Items", [])
    return _response(200, {"items": items})

def get_todo(todo_id: str):
    if not todo_id:
        return _response(400, {"message": "Missing id"})
    resp = table().get_item(Key={"id": todo_id})
    item = resp.get("Item")
    if not item:
        return _response(404, {"message": "Not found"})
    return _response(200, item)

def update_todo(todo_id: str, event):
    if not todo_id:
        return _response(400, {"message": "Missing id"})
    payload = json.loads(event.get("body") or "{}")
    data = TodoUpdate(**payload)

    updates = []
    expr_values = {}
    if data.title is not None:
        updates.append("title = :t")
        expr_values[":t"] = data.title
    if data.description is not None:
        updates.append("description = :d")
        expr_values[":d"] = data.description
    if data.status is not None:
        updates.append("status = :s")
        expr_values[":s"] = data.status
    updates.append("updated_at = :u")
    expr_values[":u"] = TodoItem.now_iso()

    if not expr_values:
        return _response(400, {"message": "Nothing to update"})

    resp = table().update_item(
        Key={"id": todo_id},
        UpdateExpression="SET " + ", ".join(updates),
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )
    return _response(200, resp.get("Attributes", {}))

def delete_todo(todo_id: str):
    if not todo_id:
        return _response(400, {"message": "Missing id"})
    table().delete_item(Key={"id": todo_id})
    return _response(204, {})
