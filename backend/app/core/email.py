# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Email sending utilities for transactional messages.

Currently supports a single operation: sending a password-reset email.
All network I/O is wrapped in :func:`asyncio.to_thread` so the async
event loop is never blocked by the synchronous :mod:`smtplib` calls.
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_password_reset_message(to_address: str, reset_url: str) -> MIMEMultipart:
    """Construct the MIME message for a password-reset email.

    Args:
        to_address: The recipient's email address.
        reset_url: The full URL the user should follow to reset their password.

    Returns:
        A :class:`~email.mime.multipart.MIMEMultipart` message ready to send.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your TradeSensei password"
    msg["From"] = settings.email_from or ""
    msg["To"] = to_address

    plain_body = (
        "You requested a password reset for your TradeSensei account.\n\n"
        f"Click the link below to set a new password:\n{reset_url}\n\n"
        "This link is valid for 1 hour and can only be used once.\n\n"
        "If you did not request a password reset, you can safely ignore this email.\n"
    )

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; color: #111; max-width: 560px; 
    margin: 0 auto; padding: 24px;">
  <h2 style="margin-bottom: 8px;">Reset your TradeSensei password</h2>
  <p>You requested a password reset for your TradeSensei account.</p>
  <p style="margin: 24px 0;">
    <a href="{reset_url}"
       style="background: #2563eb; color: #fff; padding: 12px 24px;
              text-decoration: none; border-radius: 6px; font-weight: 600;">
      Reset password
    </a>
  </p>
  <p style="color: #555; font-size: 14px;">
    This link is valid for <strong>1 hour</strong> and can only be used once.
  </p>
  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
  <p style="color: #888; font-size: 12px;">
    If you did not request a password reset, you can safely ignore this email.
    Your password will not change.
  </p>
</body>
</html>"""

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def _send_smtp(to_address: str, reset_url: str) -> None:
    """Send the password-reset email synchronously via SMTP.

    This function is intended to be called via :func:`asyncio.to_thread`
    so it does not block the event loop.

    Args:
        to_address: Recipient email address.
        reset_url: Password-reset URL to embed in the message.

    Raises:
        :class:`smtplib.SMTPException`: On any SMTP-level error.
    """
    msg = _build_password_reset_message(to_address, reset_url)

    with smtplib.SMTP(settings.smtp_host or "", settings.smtp_port) as smtp:
        if settings.smtp_tls:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(
            from_addr=settings.email_from or "",
            to_addrs=[to_address],
            msg=msg.as_string(),
        )


async def send_password_reset_email(to_address: str, reset_url: str) -> None:
    """Send a password-reset email to the given address asynchronously.

    Wraps the synchronous SMTP call in :func:`asyncio.to_thread` so the
    FastAPI event loop is not blocked.  Logs a warning and suppresses the
    exception if sending fails, so a transient SMTP error does not surface
    a 500 to the caller (the endpoint always returns 200 regardless).

    Args:
        to_address: The recipient's email address.
        reset_url: The full password-reset URL to include in the email.
    """
    try:
        await asyncio.to_thread(_send_smtp, to_address, reset_url)
        logger.info("Password-reset email sent to %s", to_address)
    except Exception:
        logger.warning("Failed to send password-reset email to %s", to_address, exc_info=True)
