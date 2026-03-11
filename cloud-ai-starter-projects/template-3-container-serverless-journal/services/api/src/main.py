"""
uvicorn entrypoint for container deployment.

    uvicorn src.main:app --host 0.0.0.0 --port 8080

Business logic → src/core/handlers.py
FastAPI wiring  → src/adapters/fastapi/app.py
Lambda direct   → src/lambda_handler.py
Lambda+Mangum   → src/lambda_mangum.py
"""

from .adapters.fastapi.app import app  # re-exported for uvicorn

__all__ = ["app"]
