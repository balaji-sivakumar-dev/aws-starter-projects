"""
Auth dependency — supports two modes controlled by APP_ENV:

  local  →  reads X-User-Id request header (no token required).
             Falls back to "dev-user" when the header is absent.
             Never used in production.

  aws    →  verifies a Cognito-issued JWT (RS256) against the pool's JWKS.
             JWKS is pre-fetched at startup and cached in memory.
"""

import logging
import os
from typing import Optional

from fastapi import Header, HTTPException
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

APP_ENV: str = os.getenv("APP_ENV", "local")
COGNITO_ISSUER: str = os.getenv("COGNITO_ISSUER", "")
COGNITO_CLIENT_ID: str = os.getenv("COGNITO_CLIENT_ID", "")

# Populated at application startup for AWS mode (see main.py lifespan)
jwks_cache: Optional[dict] = None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "UNAUTHORIZED", "message": "missing valid token"},
    )


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None, alias="x-user-id"),
) -> str:
    # ── Local / dev mode ─────────────────────────────────────────────────────
    if APP_ENV == "local":
        return x_user_id or "dev-user"

    # ── AWS / Cognito mode ────────────────────────────────────────────────────
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized()

    token = authorization.removeprefix("Bearer ").strip()

    if not jwks_cache:
        logger.error("JWKS not loaded — cannot verify token")
        raise HTTPException(
            status_code=503,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "auth service not ready"},
        )

    try:
        payload = jwt.decode(
            token,
            jwks_cache,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=COGNITO_ISSUER,
        )
        user_id = str(payload.get("sub") or "")
        if not user_id:
            raise _unauthorized()
        return user_id
    except JWTError:
        raise _unauthorized()
