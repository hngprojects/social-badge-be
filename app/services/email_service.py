import asyncio
import html
import logging

import resend
import resend.exceptions

from app.core.config import settings
from app.core.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY

VERIFICATION_SUBJECT = "Verify your Social Badge account"
ACCOUNT_LOCK_SUBJECT = "Your Social Badge account has been locked"
PASSWORD_RESET_SUBJECT = "Reset your Social Badge password"  # noqa: S105
CONTACT_NOTIFICATION_SUBJECT = "New Contact Form Submission — Social Badge"
CONTACT_CONFIRMATION_SUBJECT = "We received your message — Social Badge"


def _build_verification_html(token: str) -> str:
    return (
        "<h2>Welcome to Social Badge</h2>"
        "<p>Please verify your email address by clicking the link below:</p>"
        f'<p><a href="{settings.FRONTEND_URL}/verify?token={token}">'
        "Verify Email</a></p>"
        "<p>This link expires in 30 minutes.</p>"
    )


def _build_account_lock_html() -> str:
    minutes = settings.LOCKOUT_WINDOW // 60
    return (
        "<h2>Your Social Badge account has been temporarily locked</h2>"
        "<p>We detected too many failed login attempts on your account.</p>"
        f"<p>Your account has been locked for {minutes} minutes. "
        "Please try again after that time.</p>"
        "<p>If this wasn't you, we recommend changing your password "
        "once you regain access.</p>"
    )


def _build_password_reset_html(token: str) -> str:
    return (
        "<h2>Password Reset Request</h2>"
        "<p>We received a request to reset your Social Badge password. "
        "Click the link below to set a new password:</p>"
        f'<p><a href="{settings.FRONTEND_URL}/reset-password?token={token}">'
        "Reset Password</a></p>"
        "<p>This link expires in 30 minutes. If you didn't request a password "
        "reset, you can safely ignore this email.</p>"
    )


def _build_notification_html(
    *,
    reference_id: str,
    first_name: str,
    last_name: str | None,
    email: str,
    subject: str,
    message: str,
) -> str:
    """HTML email sent to the Social Badge team when a contact form is submitted."""
    full_name = f"{first_name} {last_name}".strip() if last_name else first_name
    full_name = html.escape(full_name)
    email = html.escape(email)
    escaped_message = html.escape(message)
    return (
        f"<h2>New Contact Form Submission</h2>"
        f"<p><strong>Reference ID:</strong> {reference_id}</p>"
        f"<p><strong>Name:</strong> {full_name}</p>"
        f"<p><strong>Email:</strong> <a href='mailto:{email}'>{email}</a></p>"
        f"<p><strong>Topic:</strong> {subject}</p>"
        f"<hr />"
        f"<p><strong>Message:</strong></p>"
        f"<p>{escaped_message}</p>"
    )


def _build_confirmation_html(
    *,
    first_name: str,
    reference_id: str,
) -> str:
    """HTML confirmation email sent to the person who submitted the contact form."""
    safe_name = html.escape(first_name)
    return (
        f"<h2>Thanks for reaching out, {safe_name}!</h2>"
        f"<p>We've received your message and will get back to you "
        f"within one business day.</p>"
        f"<p><strong>Your reference ID:</strong> {reference_id}</p>"
        f"<p>If you need to follow up, just reply to this email and "
        f"include your reference ID.</p>"
        f"<p>— The Social Badge Team</p>"
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


async def send_account_lock_email(to: str) -> None:
    """Dispatch an account-lock notification email via Resend.

    Raises EmailDeliveryError if the Resend API call fails.
    """
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to],
        "subject": ACCOUNT_LOCK_SUBJECT,
        "html": _build_account_lock_html(),
    }

    try:
        await asyncio.to_thread(resend.Emails.send, params)
    except resend.exceptions.ResendError as exc:
        logger.exception("Failed to send account lock email to %s", to)
        raise EmailDeliveryError(f"Failed to send account lock email to {to}") from exc


async def send_password_reset_email(to: str, token: str) -> None:
    """Dispatch a password reset email via Resend.

    Raises EmailDeliveryError if the Resend API call fails so the
    caller can decide how to handle the failure.
    """
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to],
        "subject": PASSWORD_RESET_SUBJECT,
        "html": _build_password_reset_html(token),
    }

    try:
        await asyncio.to_thread(resend.Emails.send, params)
    except resend.exceptions.ResendError as exc:
        logger.exception("Failed to send password reset email to %s", to)
        raise EmailDeliveryError(
            f"Failed to send password reset email to {to}"
        ) from exc


async def send_contact_notification(
    *,
    reference_id: str,
    first_name: str,
    last_name: str | None,
    email: str,
    subject: str,
    message: str,
) -> None:
    """Send a notification email to the Social Badge team.

    Raises EmailDeliveryError if the Resend API call fails.
    """
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [settings.CONTACT_RECIPIENT_EMAIL],
        "reply_to": email,
        "subject": CONTACT_NOTIFICATION_SUBJECT,
        "html": _build_notification_html(
            reference_id=reference_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            subject=subject,
            message=message,
        ),
    }
    try:
        await asyncio.to_thread(resend.Emails.send, params)
    except resend.exceptions.ResendError as exc:
        logger.exception("Failed to send contact notification for ref %s", reference_id)
        raise EmailDeliveryError(
            f"Failed to send contact notification for {reference_id}"
        ) from exc


async def send_contact_confirmation(
    *,
    to_email: str,
    first_name: str,
    reference_id: str,
) -> None:
    """Send an auto-reply confirmation to the person who submitted the form.

    Failures are logged but do not raise — the submission itself succeeded.
    """
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": CONTACT_CONFIRMATION_SUBJECT,
        "html": _build_confirmation_html(
            first_name=first_name,
            reference_id=reference_id,
        ),
    }
    try:
        await asyncio.to_thread(resend.Emails.send, params)
    except resend.exceptions.ResendError:
        logger.exception(
            "Failed to send contact confirmation to %s (ref %s)",
            to_email,
            reference_id,
        )
