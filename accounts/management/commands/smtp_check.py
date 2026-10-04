"""
Diagnostic command for the OTP email pipeline.

Usage:
    python manage.py smtp_check                 # sends to SMTP_EMAIL
    python manage.py smtp_check you@gmail.com   # sends to a specific inbox
"""

import smtplib
import ssl

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts import otp


class _ProbeUser:
    """Minimal stand-in for User — send_otp_email only needs a few attributes."""

    first_name = "MoneyMate"
    username = "smtp_check"

    def __init__(self, email):
        self.email = email


class Command(BaseCommand):
    help = "Check the Gmail SMTP settings and send a test OTP email."

    def add_arguments(self, parser):
        parser.add_argument(
            "email", nargs="?", default="",
            help="Recipient inbox (defaults to SMTP_EMAIL from .env).",
        )

    def handle(self, *args, **options):
        recipient = (options["email"] or settings.SMTP_EMAIL or "").strip()
        if not recipient:
            raise CommandError(
                "No recipient given and SMTP_EMAIL is not set. "
                "Usage: python manage.py smtp_check you@gmail.com"
            )

        self.stdout.write(f"Host : {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        self.stdout.write(f"From : {settings.SMTP_EMAIL or '(not set!)'}")
        self.stdout.write(f"To   : {recipient}")

        if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
            raise CommandError(
                "SMTP_EMAIL / SMTP_PASSWORD are missing from the environment. "
                "Copy .env.example to .env and fill them in, then restart the server."
            )

        # 1) Connection + login test (no email sent yet).
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            self.stdout.write(self.style.SUCCESS("SMTP login: OK"))
        except Exception as exc:
            raise CommandError(
                f"SMTP login FAILED ({type(exc).__name__}): {exc}\n"
                "Fix: SMTP_PASSWORD must be a Google App Password generated for the "
                "SAME account as SMTP_EMAIL (https://myaccount.google.com/apppasswords, "
                "requires 2FA). Then restart the server."
            )

        # 2) Send a real test email with the branded template.
        code = otp.generate_otp()
        ok, reason = otp.send_otp_email(_ProbeUser(recipient), code)
        if not ok:
            raise CommandError(f"Send FAILED: {reason}")

        self.stdout.write(self.style.SUCCESS(
            f"Test email SENT to {recipient} (code {code}).\n"
            "If it doesn't arrive within ~2 minutes, check the Spam / Promotions "
            "tab — brand-new Gmail senders are frequently filtered there on "
            "first contact."
        ))