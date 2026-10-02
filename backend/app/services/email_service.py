"""Best-effort transactional email.

The portal has no mail provider configured by default, and inventing one would
be worse than saying so: ``send_email`` returns False and logs
``email_not_configured`` when SMTP_HOST is unset, and the caller decides what
that means. For a password reset the honest behaviour is to keep the endpoint's
response identical (so it stays enumeration-resistant) and to log a warning --
never to log the reset link in production, where logs are shipped around.
"""

from __future__ import annotations

import asyncio
import smtplib
import ssl
import structlog
from email.message import EmailMessage

from app.core.config import settings

logger = structlog.get_logger(__name__)


async def send_email(*, to: str, subject: str, body: str) -> bool:
    if not settings.SMTP_HOST:
        logger.warning(
            "email_not_configured",
            to=to,
            subject=subject,
            hint="set SMTP_HOST/SMTP_PORT/SMTP_FROM to enable outbound email",
        )
        return False

    def _send() -> None:
        message = EmailMessage()
        message["From"] = settings.SMTP_FROM
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls(context=ssl.create_default_context())
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)

    try:
        # smtplib is blocking; a slow SMTP server must not stall the event loop.
        await asyncio.to_thread(_send)
        logger.info("email_sent", to=to, subject=subject)
        return True
    except Exception:
        logger.exception("email_send_failed", to=to, subject=subject)
        return False
