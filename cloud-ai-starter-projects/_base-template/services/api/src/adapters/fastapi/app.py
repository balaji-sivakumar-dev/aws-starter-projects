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
from .admin_routes import router as admin_router
from .config_routes import router as config_router
from .insights_routes import router as insights_router
from .rag_routes import router as rag_router
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


def _wait_for_dynamo(retries: int = 15, delay: float = 2.0) -> None:
    """
    Poll until DynamoDB local is accepting requests.

    Uses a raw HTTP POST (DynamoDB ListTables wire format) because boto3's
    default HTTP client can hang indefinitely on the first connection
    to dynamodb-local while it warms up. Any HTTP response (including a 400
    auth error) confirms the service is ready — the actual table creation
    that follows will use proper credentials.
    """
    import urllib.error
    import urllib.request

    endpoint = os.getenv("DYNAMODB_ENDPOINT", "http://dynamodb-local:8000")

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                endpoint,
                method="POST",
                data=b"{}",
                headers={
                    "Content-Type": "application/x-amz-json-1.0",
                    "X-Amz-Target": "DynamoDB_20120810.ListTables",
                },
            )
            urllib.request.urlopen(req, timeout=3)
            logger.info("DynamoDB is reachable.")
            return
        except urllib.error.HTTPError as exc:
            # Any HTTP response (incl. 400 auth error) = DynamoDB is up
            logger.info("DynamoDB is reachable (HTTP %d).", exc.code)
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
        title="{{APP_TITLE}} API",
        description=(
            "Containerised Python API.\n\n"
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
    app.include_router(config_router)
    app.include_router(insights_router)
    app.include_router(rag_router)
    app.include_router(admin_router)
    return app


app = create_app()
