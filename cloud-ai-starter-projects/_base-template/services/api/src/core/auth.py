"""
Pure auth logic — no web framework imports.
Both the FastAPI adapter and Lambda adapter call these functions.
"""

import os
from typing import Optional

from jose import JWTError, jwt

APP_ENV: str = os.getenv("APP_ENV", "local")
COGNITO_ISSUER: str = os.getenv("COGNITO_ISSUER", "")
COGNITO_CLIENT_ID: str = os.getenv("COGNITO_CLIENT_ID", "")

# Populated at application startup in AWS mode (see adapters/fastapi/app.py)
jwks_cache: Optional[dict] = None


def resolve_user_local(x_user_id: Optional[str]) -> str:
    """Local dev: use the X-User-Id header value, falling back to 'dev-user'."""
    return (x_user_id or "").strip() or "dev-user"


def resolve_user_cognito(bearer_token: str) -> str:
    """
    Verify a Cognito JWT and return the subject (user ID).
    Raises ValueError on any failure so adapters can map it to 401.
    """
    if not jwks_cache:
        raise ValueError("JWKS not loaded")
    try:
        payload = jwt.decode(
            bearer_token,
            jwks_cache,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=COGNITO_ISSUER,
        )
        user_id = str(payload.get("sub") or "")
        if not user_id:
            raise ValueError("missing sub claim")
        return user_id
    except JWTError as exc:
        raise ValueError(f"invalid token: {exc}") from exc


def resolve_email_cognito(bearer_token: str) -> str:
    """
    Decode a Cognito JWT (already verified) and return the email claim.
    Assumes token is valid — call after resolve_user_cognito succeeds.
    """
    if not jwks_cache:
        raise ValueError("JWKS not loaded")
    try:
        payload = jwt.decode(
            bearer_token,
            jwks_cache,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=COGNITO_ISSUER,
        )
        return str(payload.get("email") or "").strip().lower()
    except JWTError as exc:
        raise ValueError(f"invalid token: {exc}") from exc
