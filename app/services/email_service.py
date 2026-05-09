import asyncio
import logging

import resend

from app.core.config import settings
from app.core.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY

VERIFICATION_SUBJECT = "Verify your Social Badge account"


def _build_verification_html(token: str) -> str:
    return (
        "<h2>Welcome to Social Badge</h2>"
        "<p>Please verify your email address by clicking the link below:</p>"
        f'<p><a href="{settings.FRONTEND_URL}/verify?token={token}">'
        "Verify Email</a></p>"
        "<p>This link expires in 30 minutes.</p>"
    )


async def send_verification_email(to: str, token: str) -> None:
    """Dispatch a verification email via Resend.

    Raises EmailDeliveryError if the Resend API call fails so the
    caller can decide how to handle the failure.
    """
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to],
        "subject": VERIFICATION_SUBJECT,
        "html": _build_verification_html(token),
    }

    try:
        await asyncio.to_thread(resend.Emails.send, params)
    except resend.exceptions.ResendError as exc:
        logger.exception("Failed to send verification email to %s", to)
        raise EmailDeliveryError(f"Failed to send verification email to {to}") from exc
