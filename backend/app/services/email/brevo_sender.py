"""Brevo-backed transactional email sender.

OTP generation and verification stay in the application. This module only
delivers the already-generated code.
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

from brevo import Brevo
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailSender(Protocol):
    def send_verification_otp(self, *, to: str, otp: str) -> None: ...


class EmailDeliveryError(AppException):
    status_code = 502
    error_code = "email_delivery_failed"
    message = "Could not send the verification email. Please try again."


def _otp_html(otp: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verify Your Email</title>
    </head>
    <body style="margin:0;padding:0;background-color:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
        <div style="max-width:600px;margin:40px auto;background-color:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;">
            <div style="padding:28px 32px;background-color:#111827;text-align:center;">
                <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:600;">
                    {settings.app.name}
                </h1>
            </div>
            <div style="padding:40px 32px;">
                <h2 style="margin:0 0 16px;font-size:22px;color:#111827;">
                    Verify your email address
                </h2>
                <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#4b5563;">
                    Thank you for registering with {settings.app.name}.
                    Please use the verification code below to verify
                    your email address and complete your registration.
                </p>
                <div style="margin:30px 0;padding:22px;background-color:#f3f4f6;border-radius:10px;text-align:center;">
                    <p style="margin:0 0 8px;font-size:13px;color:#6b7280;">
                        Your verification code
                    </p>
                    <div style="font-size:32px;font-weight:700;letter-spacing:8px;color:#111827;">
                        {otp}
                    </div>
                </div>
                <p style="margin:0 0 12px;font-size:14px;line-height:1.5;color:#4b5563;">
                    This verification code will expire in
                    <strong>{settings.email_verification.otp_ttl_minutes} minutes</strong>.
                </p>
                <p style="margin:0 0 24px;font-size:14px;line-height:1.5;color:#4b5563;">
                    If you did not create an account with {settings.app.name},
                    you can safely ignore this email.
                </p>
                <hr style="border:0;border-top:1px solid #e5e7eb;margin:28px 0;">
                <p style="margin:0;font-size:12px;line-height:1.5;color:#9ca3af;text-align:center;">
                    This is an automated email. Please do not reply to this message.
                </p>
            </div>
            <div style="padding:20px 32px;background-color:#f9fafb;text-align:center;">
                <p style="margin:0;font-size:12px;color:#9ca3af;">
                    © 2026 {settings.app.name}. All rights reserved.
                </p>
            </div>
        </div>
    </body>
    </html>
    """


class BrevoEmailSender:
    def send_verification_otp(self, *, to: str, otp: str) -> None:
        api_key = (settings.BREVO_API_KEY or "").strip()
        sender_email = (settings.email.from_address or "").strip()
        smtp_login = (settings.email.smtp_login or "").strip() or None
        if not api_key:
            raise EmailDeliveryError(
                "Email delivery is not configured. Set BREVO_API_KEY in .env."
            )
        if not sender_email:
            raise EmailDeliveryError(
                "Email sender is not configured. Set email.from_address in settings/config.yaml."
            )

        is_smtp_key = api_key.startswith("xsmtpsib-")
        if is_smtp_key and not smtp_login:
            raise EmailDeliveryError(
                "BREVO_API_KEY is a Brevo SMTP key (xsmtpsib-), not an API key. "
                "Create an API key (starts with xkeysib-) in Brevo → SMTP & API → API Keys "
                "and put it in .env as BREVO_API_KEY. "
                "Or set email.smtp_login in settings/config.yaml to the SMTP Login "
                "shown next to that SMTP key (it is not your Gmail address)."
            )

        try:
            if is_smtp_key:
                self._send_via_smtp(
                    api_key=api_key,
                    smtp_login=smtp_login or sender_email,
                    sender_email=sender_email,
                    to=to,
                    otp=otp,
                )
                return
            self._send_via_api(api_key=api_key, sender_email=sender_email, to=to, otp=otp)
        except EmailDeliveryError:
            raise
        except Exception as exc:
            logger.exception("Brevo failed to deliver verification OTP")
            detail = str(exc)
            if "535" in detail or "Authentication failed" in detail:
                raise EmailDeliveryError(
                    "Brevo SMTP login failed. Set email.smtp_login to the Login "
                    "value from Brevo → SMTP & API (not the Gmail From address)."
                ) from None
            if "unauthorized" in detail.lower() or "invalid" in detail.lower():
                raise EmailDeliveryError(
                    "Brevo rejected the API key. Use an API key (xkeysib-) from "
                    "Brevo → SMTP & API → API Keys."
                ) from None
            raise EmailDeliveryError() from None

    def _send_via_api(
        self, *, api_key: str, sender_email: str, to: str, otp: str
    ) -> None:
        client = Brevo(api_key=api_key)
        result = client.transactional_emails.send_transac_email(
            subject=f"Verify Your Email – {settings.app.name}",
            html_content=_otp_html(otp),
            sender=SendTransacEmailRequestSender(
                name=settings.email.from_name,
                email=sender_email,
            ),
            to=[SendTransacEmailRequestToItem(email=to)],
        )
        logger.info("Brevo accepted verification email message_id=%s", result.message_id)

    def _send_via_smtp(
        self,
        *,
        api_key: str,
        smtp_login: str,
        sender_email: str,
        to: str,
        otp: str,
    ) -> None:
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Verify Your Email – {settings.app.name}"
        message["From"] = f"{settings.email.from_name} <{sender_email}>"
        message["To"] = to
        message.attach(MIMEText(_otp_html(otp), "html"))
        with smtplib.SMTP("smtp-relay.brevo.com", 587, timeout=30) as server:
            server.starttls()
            server.login(smtp_login, api_key)
            server.sendmail(sender_email, [to], message.as_string())
        logger.info("Brevo SMTP accepted verification email to %s", to)
