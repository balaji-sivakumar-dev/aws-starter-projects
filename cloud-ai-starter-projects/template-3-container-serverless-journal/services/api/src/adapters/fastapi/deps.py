"""FastAPI auth dependency — wraps core/auth.py."""

import os
from typing import Optional

from fastapi import Header, HTTPException

from ...core import auth as core_auth

APP_ENV = os.getenv("APP_ENV", "local")


def _unauthorized(msg: str = "missing valid token") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "UNAUTHORIZED", "message": msg},
    )


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None, alias="x-user-id"),
) -> str:
    if APP_ENV == "local":
        return core_auth.resolve_user_local(x_user_id)

    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized()

    token = authorization.removeprefix("Bearer ").strip()
    try:
        return core_auth.resolve_user_cognito(token)
    except ValueError as exc:
        raise _unauthorized(str(exc)) from exc
