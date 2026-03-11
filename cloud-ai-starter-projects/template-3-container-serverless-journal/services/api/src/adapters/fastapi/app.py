"""FastAPI application factory — used by both the uvicorn entrypoint and Mangum."""

import logging
import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...core import auth as core_auth
from ...core import repository
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
        _wait_for_dynamo()
        repository.ensure_table()
    elif COGNITO_ISSUER:
        await _load_jwks()
    yield


def _wait_for_dynamo(retries: int = 10, delay: float = 1.0) -> None:
    import boto3

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
            logger.warning("DynamoDB not ready (%d/%d): %s", attempt, retries, exc)
            time.sleep(delay)
    logger.error("DynamoDB did not become ready — continuing anyway.")


async def _load_jwks() -> None:
    url = f"{COGNITO_ISSUER}/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            core_auth.jwks_cache = resp.json()
            logger.info("JWKS loaded from %s", url)
    except Exception as exc:
        logger.warning("Failed to load JWKS: %s", exc)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Template 3 — Journal API",
        description=(
            "Containerised Python journal API.\n\n"
            "**Deployment modes**\n"
            "- Docker container → `uvicorn` (this app directly)\n"
            "- Lambda container → Mangum wraps this app (`src.lambda_mangum`)\n"
            "- Lambda direct → thin adapter calls `core.handlers` (`src.lambda_handler`)\n"
        ),
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
    return app


app = create_app()
