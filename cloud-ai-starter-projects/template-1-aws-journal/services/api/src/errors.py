import json
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ApiError(Exception):
    status_code: int
    code: str
    message: str


def build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
        "body": json.dumps(body),
    }


def error_response(err: ApiError, request_id: str) -> Dict[str, Any]:
    return build_response(
        err.status_code,
        {
            "code": err.code,
            "message": err.message,
            "requestId": request_id,
        },
    )
