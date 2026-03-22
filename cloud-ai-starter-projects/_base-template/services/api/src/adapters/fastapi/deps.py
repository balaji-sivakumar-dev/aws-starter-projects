"""FastAPI auth dependency — wraps core/auth.py."""

import os
from typing import Optional

from fastapi import Header, HTTPException

from ...core import auth as core_auth

# Environments that bypass JWT verification and use the X-User-Id header.
# "local" → Docker Compose dev mode.
# "test"  → pytest / CI (no real DynamoDB or Cognito).
_LOCAL_ENVS = frozenset({"local", "test"})


def _unauthorized(msg: str = "missing valid token") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "UNAUTHORIZED", "message": msg},
    )


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None, alias="x-user-id"),
) -> str:
    # Read at request time so tests can set APP_ENV before importing the app.
    if os.getenv("APP_ENV", "local") in _LOCAL_ENVS:
        return core_auth.resolve_user_local(x_user_id)

    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized()

    token = authorization.removeprefix("Bearer ").strip()
    try:
        return core_auth.resolve_user_cognito(token)
    except ValueError as exc:
        raise _unauthorized(str(exc)) from exc


async def get_current_user_email(
    authorization: Optional[str] = Header(default=None),
    x_user_email: Optional[str] = Header(default=None, alias="x-user-email"),
) -> str:
    """Returns the authenticated user's email (used for admin role check)."""
    if os.getenv("APP_ENV", "local") in _LOCAL_ENVS:
        return (x_user_email or "dev-user@local").strip().lower()

    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized()

    token = authorization.removeprefix("Bearer ").strip()
    try:
        return core_auth.resolve_email_cognito(token)
    except ValueError as exc:
        raise _unauthorized(str(exc)) from exc
