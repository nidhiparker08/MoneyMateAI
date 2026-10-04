"""
Email OTP verification service.

Security properties:
- Codes are generated with ``secrets`` (cryptographically secure RNG).
- Codes are stored as HMAC-SHA256 hashes keyed with SECRET_KEY — never plain.
- Codes expire after 5 minutes, allow 5 verification attempts, and are
  invalidated the moment a new one is issued (60s resend cooldown).
- Credentials are read ONLY from environment variables and are never logged.
"""

import hashlib
import hmac
import logging
import secrets
import smtplib
import ssl
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from .models import EmailVerification

logger = logging.getLogger(__name__)

# Session key that binds an unauthenticated visitor to the OTP screen.
OTP_SESSION_KEY = "otp_pending_user_id"

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = getattr(settings, "OTP_EXPIRY_MINUTES", 5)
OTP_MAX_ATTEMPTS = getattr(settings, "OTP_MAX_ATTEMPTS", 5)
OTP_RESEND_COOLDOWN_SECONDS = getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)


# ==========================================================
# CODE HELPERS
# ==========================================================

def generate_otp() -> str:
    """Secure, zero-padded 6-digit code."""
    return f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"


def hash_otp(code: str) -> str:
    """HMAC-SHA256 of the code, keyed with SECRET_KEY."""
    return hmac.new(
        settings.SECRET_KEY.encode(), (code or "").strip().encode(), hashlib.sha256
    ).hexdigest()


def get_or_create_record(user) -> EmailVerification:
    record, _ = EmailVerification.objects.get_or_create(user=user)
    return record


def is_email_verified(user) -> bool:
    """
    Users without an EmailVerification row predate the OTP feature and are
    treated as verified — nobody is asked for OTP retroactively.
    """
    record = getattr(user, "email_verification", None)
    return record is None or record.is_verified


def mask_email(email: str) -> str:
    """j***@gmail.com — for display on the OTP screen."""
    try:
        local, domain = email.split("@", 1)
        shown = local[0] if local else ""
        return f"{shown}{'*' * max(len(local) - 1, 3)}@{domain}"
    except (ValueError, AttributeError):
        return "your email"


def cooldown_remaining(record) -> int:
    if record.otp_last_sent_at:
        elapsed = (timezone.now() - record.otp_last_sent_at).total_seconds()
        return max(0, int(OTP_RESEND_COOLDOWN_SECONDS - elapsed))
    return 0


def code_is_active(record) -> bool:
    return bool(
        record.otp_hash
        and record.otp_expiry
        and timezone.now() < record.otp_expiry
        and record.otp_attempts < OTP_MAX_ATTEMPTS
    )


def _clear_code(record):
    record.otp_hash = ""
    record.otp_expiry = None
    record.otp_attempts = 0


# ==========================================================
# ISSUE / VERIFY
# ==========================================================

def issue_otp(user, record=None, force=False) -> dict:
    """
    Generate and email a fresh OTP, invalidating any previous code.

    force=True skips the "a valid code is already active" short-circuit
    (used by the explicit resend endpoint) — the cooldown still applies.

    Returns {"status": "sent"|"active"|"cooldown"|"error",
             "message": str, "resend_in": int, "sent": bool}
    """
    record = record or get_or_create_record(user)

    # An account without an email address can never receive the code —
    # fail fast (and without consuming the cooldown) with a clear reason.
    user_email = (getattr(user, "email", "") or "").strip()
    if not user_email:
        message = (
            "This account has no email address, so a verification code "
            "cannot be sent. Sign up again with a valid email."
            if getattr(settings, "DEBUG", False)
            else "We couldn't send the email right now. Please try again in a moment."
        )
        return {
            "status": "error",
            "message": message,
            "resend_in": 0,
            "sent": False,
            "dev_code": None,
        }

    if not force and code_is_active(record):
        return {
            "status": "active",
            "message": "A code is already on its way — please check your inbox.",
            "resend_in": cooldown_remaining(record),
            "sent": True,
            "dev_code": None,
        }

    wait = cooldown_remaining(record)
    if wait > 0:
        return {
            "status": "cooldown",
            "message": f"Please wait {wait}s before requesting a new code.",
            "resend_in": wait,
            "sent": False,
            "dev_code": None,
        }

    code = generate_otp()
    record.otp_hash = hash_otp(code)
    record.otp_expiry = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    record.otp_attempts = 0
    record.otp_last_sent_at = timezone.now()
    record.save(update_fields=[
        "otp_hash", "otp_expiry", "otp_attempts", "otp_last_sent_at", "updated_at",
    ])

    ok, reason = send_otp_email(user, code)
    if ok:
        # Dev convenience: let the local developer complete the flow even if
        # Gmail filters the email. Never set outside DEBUG, never in API/DB.
        dev_code = (
            code
            if getattr(settings, "DEBUG", False)
            and getattr(settings, "OTP_SHOW_CODE_IN_DEBUG", True)
            else None
        )
        return {
            "status": "sent",
            "message": "A 6-digit verification code was sent to your email.",
            "resend_in": OTP_RESEND_COOLDOWN_SECONDS,
            "sent": True,
            "dev_code": dev_code,
        }

    # Delivery failed — clear the code and allow an immediate retry.
    _clear_code(record)
    record.otp_last_sent_at = None
    record.save(update_fields=[
        "otp_hash", "otp_expiry", "otp_attempts", "otp_last_sent_at", "updated_at",
    ])
    return {
        "status": "error",
        "message": reason or "We couldn't send the email right now. Please try again in a moment.",
        "resend_in": 0,
        "sent": False,
        "dev_code": None,
    }


def verify_code(user, code: str) -> tuple:
    """
    Check a submitted code. Never returns or logs the code itself.

    Returns (status, message, extra) where status is one of:
    "success" | "invalid" | "expired" | "locked"
    and extra = {"attempts_left": int, "resend_in": int}
    """
    record = get_or_create_record(user)
    extra = {
        "attempts_left": max(0, OTP_MAX_ATTEMPTS - record.otp_attempts),
        "resend_in": cooldown_remaining(record),
    }

    if record.is_verified:
        return "success", "Email already verified.", extra

    code = (code or "").strip()
    if not code.isdigit() or len(code) != OTP_LENGTH:
        return "invalid", f"Enter the {OTP_LENGTH}-digit code from your email.", extra

    if not record.otp_hash:
        return "expired", "No active code — request a new one below.", extra

    if record.otp_attempts >= OTP_MAX_ATTEMPTS:
        return "locked", "Too many incorrect attempts — request a new code below.", extra

    if record.otp_expiry and timezone.now() >= record.otp_expiry:
        _clear_code(record)
        record.save(update_fields=["otp_hash", "otp_expiry", "otp_attempts", "updated_at"])
        return "expired", "That code has expired — request a new one below.", extra

    if hmac.compare_digest(record.otp_hash, hash_otp(code)):
        record.is_verified = True
        record.verified_at = timezone.now()
        _clear_code(record)
        record.save(update_fields=[
            "is_verified", "verified_at", "otp_hash", "otp_expiry", "otp_attempts", "updated_at",
        ])
        return "success", "Email verified.", extra

    record.otp_attempts += 1
    extra["attempts_left"] = max(0, OTP_MAX_ATTEMPTS - record.otp_attempts)
    if record.otp_attempts >= OTP_MAX_ATTEMPTS:
        _clear_code(record)
        record.save(update_fields=["otp_hash", "otp_expiry", "otp_attempts", "updated_at"])
        return "locked", "Too many incorrect attempts — request a new code below.", extra

    record.save(update_fields=["otp_attempts", "updated_at"])
    return "invalid", f"Incorrect code — {extra['attempts_left']} attempt(s) remaining.", extra


# ==========================================================
# EMAIL DELIVERY (Gmail SMTP · STARTTLS)
# ==========================================================

def _build_plain_text(user, code: str) -> str:
    name = user.first_name or user.username
    return (
        f"Hi {name},\n\n"
        f"Your MoneyMate verification code is:\n\n{code}\n\n"
        f"This code expires in {OTP_EXPIRY_MINUTES} minutes.\n"
        f"Do not share this code with anyone.\n\n"
        f"Didn't request this? You can safely ignore this email.\n\n"
        f"— MoneyMate"
    )


def send_otp_email(user, code: str) -> tuple:
    """
    Deliver the branded OTP email via Gmail SMTP (STARTTLS).

    Returns (ok, reason): ``reason`` is "" on success, otherwise a safe,
    human-readable failure explanation (detailed only when DEBUG is on).
    Credentials are read from environment variables only and never logged.
    """
    debug = getattr(settings, "DEBUG", False)
    smtp_email = getattr(settings, "SMTP_EMAIL", "")
    smtp_password = getattr(settings, "SMTP_PASSWORD", "")

    # Guard against empty/missing recipient (Gmail answers 555 syntax error).
    if not (getattr(user, "email", "") or "").strip():
        logger.error("OTP email delivery failed: user %s has no email address.", mask_email(getattr(user, "email", "")))
        return False, (
            "This account has no email address, so a verification code cannot be sent."
            if debug
            else "We couldn't send the email right now. Please try again in a moment."
        )

    if not smtp_email or not smtp_password:
        # Local development without SMTP configured — surface the code on the
        # runserver console only (never in production, DEBUG is off there).
        if debug:
            logger.warning(
                "[DEV ONLY] SMTP not configured — OTP for %s is %s",
                mask_email(user.email), code,
            )
            return False, (
                "SMTP is not configured (.env) — the code was printed to the "
                "runserver console instead."
            )
        logger.error("SMTP is not configured — cannot send OTP email.")
        return False, "We couldn't send the email right now. Please try again in a moment."

    html_body = render_to_string("emails/otp_email.html", {
        "user": user,
        "otp": code,
        "expiry_minutes": OTP_EXPIRY_MINUTES,
    })

    message = MIMEMultipart("alternative")
    message["Subject"] = "Your MoneyMate verification code"
    message["From"] = f"MoneyMate <{smtp_email}>"
    message["To"] = user.email
    message.attach(MIMEText(_build_plain_text(user, code), "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST, settings.SMTP_PORT, timeout=15
        ) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(smtp_email, smtp_password)
            server.send_message(message)
        return True, ""
    except smtplib.SMTPAuthenticationError:
        logger.error("OTP email delivery failed: SMTP authentication rejected.")
        return False, (
            "SMTP login rejected — SMTP_EMAIL and SMTP_PASSWORD don't match. "
            "A Google App Password only works for the account that created it "
            "(check .env)."
            if debug
            else "We couldn't send the email right now. Please try again in a moment."
        )
    except (smtplib.SMTPException, OSError) as exc:
        # Log the failure type only — never credentials, never the code.
        logger.exception("OTP email delivery failed.")
        return False, (
            f"Mail server error: {type(exc).__name__} — {exc}"
            if debug
            else "We couldn't send the email right now. Please try again in a moment."
        )