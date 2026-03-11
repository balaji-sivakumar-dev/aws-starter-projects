"""
Journal API — FastAPI entry point.

Startup behaviour:
  local  →  auto-creates the DynamoDB table if missing (against dynamodb-local).
  aws    →  fetches Cognito JWKS and caches them for JWT verification.
"""

import logging
import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth, repository
from .routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

APP_ENV = os.getenv("APP_ENV", "local")
COGNITO_ISSUER = os.getenv("COGNITO_ISSUER", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if APP_ENV == "local":
        # Give dynamodb-local a moment to be ready, then create the table
        _wait_for_dynamo()
        repository.ensure_table()
    else:
        # Pre-fetch Cognito JWKS so the first request isn't slow
        if COGNITO_ISSUER:
            await _load_jwks()
    yield


def _wait_for_dynamo(retries: int = 10, delay: float = 1.0) -> None:
    """Retry loop so the API doesn't crash if dynamodb-local is still starting."""
    import boto3
    from botocore.exceptions import EndpointResolutionError, NoRegionError

    endpoint = os.getenv("DYNAMODB_ENDPOINT", "")
    for attempt in range(1, retries + 1):
        try:
            boto3.client(
                "dynamodb",
                endpoint_url=endpoint or None,
                region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            ).list_tables()
            logger.info("DynamoDB is reachable.")
            return
        except Exception as exc:
            logger.warning("DynamoDB not ready (attempt %d/%d): %s", attempt, retries, exc)
            time.sleep(delay)
    logger.error("DynamoDB did not become ready — continuing anyway.")


async def _load_jwks() -> None:
    jwks_url = f"{COGNITO_ISSUER}/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            auth.jwks_cache = resp.json()
            logger.info("JWKS loaded from %s", jwks_url)
    except Exception as exc:
        logger.warning("Failed to load JWKS from %s: %s", jwks_url, exc)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Template 3 — Journal API",
    description="Containerised journal API (Python FastAPI + DynamoDB).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
