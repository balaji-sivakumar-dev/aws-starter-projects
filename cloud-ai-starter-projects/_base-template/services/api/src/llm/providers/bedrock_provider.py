"""
AWS Bedrock LLM provider using the Converse API.

Supports any Bedrock model that implements the Converse API:
  - Amazon Nova  (amazon.nova-lite-v1:0, amazon.nova-pro-v1:0)  ← default
  - Anthropic Claude (anthropic.claude-3-haiku-20240307-v1:0, etc.)

Override the model via BEDROCK_MODEL_ID environment variable.

No API key needed — authentication is handled by the IAM role attached to
the Lambda / execution environment.

IAM requirement (managed by Terraform in infra/terraform/modules/):
  bedrock:InvokeModel on the model ARN
"""

import logging
import os
from typing import Any, Dict, List

from ..interface import LLMProvider

logger = logging.getLogger(__name__)


class BedrockProvider(LLMProvider):
    """LLM provider backed by AWS Bedrock via the Converse API."""

    DEFAULT_MODEL = "amazon.nova-lite-v1:0"

    def __init__(self) -> None:
        import boto3  # lazy import — not available in local dev without AWS credentials

        self.model = os.getenv("BEDROCK_MODEL_ID", self.DEFAULT_MODEL)
        self.client = boto3.client("bedrock-runtime")
        logger.info("BedrockProvider initialised (model=%s)", self.model)

    def _complete(self, prompt: str, max_tokens: int = 512) -> str:
        """Call the Bedrock Converse API and return the text response."""
        response = self.client.converse(
            modelId=self.model,
            messages=[
                {"role": "user", "content": [{"text": prompt}]}
            ],
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": 0.3,
            },
        )
        return response["output"]["message"]["content"][0]["text"]

    def enrich(self, title: str, body: str) -> Dict[str, Any]:
        raw = self._complete(self.build_prompt(title, body), max_tokens=512)
        return self.parse_response(raw)

    def analyze_period(self, entries: List[Dict[str, Any]], period_label: str) -> Dict[str, Any]:
        raw = self._complete(
            self.build_period_prompt(entries, period_label),
            max_tokens=1024,
        )
        return self.parse_period_response(raw)
