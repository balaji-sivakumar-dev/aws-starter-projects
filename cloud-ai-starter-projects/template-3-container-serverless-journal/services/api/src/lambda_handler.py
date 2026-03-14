"""
Lambda direct-handler entrypoint.

Deploy as a Lambda function (zip or container) with:
    Handler: src.lambda_handler.handler

This bypasses FastAPI entirely — minimal cold start, no ASGI overhead.
Business logic lives in core/handlers.py and is shared with the FastAPI adapter.
"""

from .adapters.lambda_.handler import handler  # noqa: F401  (re-exported)

__all__ = ["handler"]
