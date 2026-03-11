"""
Lambda-via-Mangum entrypoint.

Deploy the FastAPI app as a Lambda container image using Mangum as the
ASGI-to-Lambda bridge. The entire FastAPI stack (routes, middleware, auth)
runs unchanged inside Lambda.

    Handler: src.lambda_mangum.handler

When to use this vs lambda_handler.py:
  - Use Mangum  → you want the full FastAPI stack (Swagger UI, middleware, etc.)
                  in Lambda without maintaining a separate handler.
  - Use direct  → you want the smallest possible Lambda with no FastAPI overhead.

Requires:  pip install mangum  (included in requirements-lambda.txt)
"""

from mangum import Mangum

from .adapters.fastapi.app import app

# lifespan="off" because Lambda initializes the app fresh per container,
# not per-request; the lifespan context manager is called once at cold start.
handler = Mangum(app, lifespan="off")

__all__ = ["handler"]
