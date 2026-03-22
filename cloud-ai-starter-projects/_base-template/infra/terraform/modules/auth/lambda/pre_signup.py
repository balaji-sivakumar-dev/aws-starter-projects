"""
Cognito Pre-Signup Lambda trigger.

Checks the registering user's email against an allowlist stored in
SSM Parameter Store at /<app_prefix>/<env>/cognito/allowed_emails.

The parameter value is a newline- or comma-separated list of email addresses.
Admins can update it in the AWS console (Systems Manager → Parameter Store)
without touching infrastructure.

If the email is NOT on the list the Lambda raises an exception — Cognito
will reject the sign-up and show an error to the user.
"""

import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SSM_PARAM = os.environ.get("ALLOWED_EMAILS_SSM_PATH", "")


def _get_allowed_emails() -> set[str]:
    """Fetch and parse the allowlist from SSM (no caching — Lambda is cold-started rarely)."""
    if not SSM_PARAM:
        logger.error("ALLOWED_EMAILS_SSM_PATH env var not set — rejecting all sign-ups.")
        return set()

    ssm = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    try:
        resp = ssm.get_parameter(Name=SSM_PARAM, WithDecryption=True)
        value = resp["Parameter"]["Value"]
        # Accept newline or comma separated
        emails = {e.strip().lower() for e in value.replace(",", "\n").splitlines() if e.strip()}
        logger.info("Loaded %d allowed emails from SSM.", len(emails))
        return emails
    except ssm.exceptions.ParameterNotFound:
        logger.error("SSM parameter %s not found — rejecting all sign-ups.", SSM_PARAM)
        return set()
    except Exception as exc:
        logger.error("Failed to read SSM parameter: %s", exc)
        return set()


def handler(event, context):
    """Cognito pre-signup trigger entry point."""
    email = (
        event.get("request", {})
        .get("userAttributes", {})
        .get("email", "")
        .strip()
        .lower()
    )

    logger.info("Pre-signup check for email: %s", email)

    if not email:
        raise Exception("Email attribute is required for registration.")

    allowed = _get_allowed_emails()
    if email not in allowed:
        logger.warning("Blocked sign-up attempt: %s not in allowlist.", email)
        raise Exception(
            "Registration is by invitation only. "
            "Contact the administrator to request access."
        )

    logger.info("Allowing sign-up for: %s", email)
    # Return the event unchanged — Cognito proceeds with registration
    return event
