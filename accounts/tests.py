"""
Email OTP verification tests.

Run with:  python manage.py test accounts

The real SMTP sender is patched out - no emails are sent during tests.
"""

import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone

from . import otp
from .models import EmailVerification

User = get_user_model()

SEND_PATH = "accounts.otp.send_otp_email"


class OTPServiceTest(TestCase):
    """Core OTP service: hashing, expiry, attempts, cooldown."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="aarav", email="aarav@example.com", password="Test@12345"
        )
        self.record = otp.get_or_create_record(self.user)

    def test_otp_is_hashed_not_plain(self):
        code = otp.generate_otp()
        self.record.otp_hash = otp.hash_otp(code)
        self.record.save()
        self.assertNotEqual(self.record.otp_hash, code)
        self.assertEqual(len(self.record.otp_hash), 64)

    def test_generate_otp_format(self):
        for _ in range(50):
            code = otp.generate_otp()
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isdigit())

    def test_verify_correct_code(self):
        code = otp.generate_otp()
        self.record.otp_hash = otp.hash_otp(code)
        self.record.otp_expiry = timezone.now() + datetime.timedelta(minutes=5)
        self.record.save()

        status, _, _ = otp.verify_code(self.user, code)
        self.assertEqual(status, "success")
        self.record.refresh_from_db()
        self.assertTrue(self.record.is_verified)
        self.assertEqual(self.record.otp_hash, "")  # single use
        self.assertEqual(self.record.otp_attempts, 0)

    def test_verify_wrong_code_increments_attempts(self):
        self.record.otp_hash = otp.hash_otp("123456")
        self.record.otp_expiry = timezone.now() + datetime.timedelta(minutes=5)
        self.record.save()

        status, message, extra = otp.verify_code(self.user, "654321")
        self.assertEqual(status, "invalid")
        self.assertEqual(extra["attempts_left"], otp.OTP_MAX_ATTEMPTS - 1)
        self.assertNotIn("123456", message)  # never leak the code

    def test_max_attempts_locks_code(self):
        self.record.otp_hash = otp.hash_otp("123456")
        self.record.otp_expiry = timezone.now() + datetime.timedelta(minutes=5)
        self.record.save()

        for _ in range(otp.OTP_MAX_ATTEMPTS):
            status, _, _ = otp.verify_code(self.user, "000000")
        self.assertEqual(status, "locked")
        self.record.refresh_from_db()
        self.assertEqual(self.record.otp_hash, "")  # invalidated

    def test_expired_code_rejected(self):
        self.record.otp_hash = otp.hash_otp("123456")
        self.record.otp_expiry = timezone.now() - datetime.timedelta(seconds=1)
        self.record.save()

        status, _, _ = otp.verify_code(self.user, "123456")
        self.assertEqual(status, "expired")

    def test_resend_cooldown(self):
        with mock.patch(SEND_PATH, return_value=(True, "")):
            first = otp.issue_otp(self.user, self.record)
            # While a valid code is active, a normal issue does not re-send.
            second = otp.issue_otp(self.user, self.record)
        self.assertEqual(first["status"], "sent")
        self.assertEqual(second["status"], "active")

        # Expire the code — an immediate re-issue now hits the cooldown.
        self.record.otp_expiry = timezone.now() - datetime.timedelta(seconds=1)
        self.record.save()
        with mock.patch(SEND_PATH, return_value=(True, "")):
            third = otp.issue_otp(self.user, self.record)
        self.assertEqual(third["status"], "cooldown")
        self.assertFalse(third["sent"])

    def test_resend_invalidates_old_code(self):
        with mock.patch(SEND_PATH, return_value=(True, "")):
            otp.issue_otp(self.user, self.record)
        old_hash = self.record.otp_hash
        # Expire (don't clear) the old code, clear the cooldown, then resend.
        self.record.otp_expiry = timezone.now() - datetime.timedelta(seconds=1)
        self.record.otp_last_sent_at = None
        self.record.save()
        with mock.patch(SEND_PATH, return_value=(True, "")):
            second = otp.issue_otp(self.user, self.record, force=True)

        self.assertEqual(second["status"], "sent")
        self.record.refresh_from_db()
        self.assertNotEqual(self.record.otp_hash, old_hash)

    def test_is_email_verified_grandfathers_existing_users(self):
        # No EmailVerification row -> treated as verified (existing users).
        legacy = User.objects.create_user(username="legacy", email="legacy@example.com")
        self.assertTrue(otp.is_email_verified(legacy))
        # Explicit verified record -> verified.
        self.record.is_verified = True
        self.record.save()
        self.assertTrue(otp.is_email_verified(self.user))
        # Explicit unverified record -> not verified.
        self.record.is_verified = False
        self.record.save()
        self.assertFalse(otp.is_email_verified(self.user))

    def test_mask_email(self):
        self.assertEqual(otp.mask_email("aarav@gmail.com"), "a****@gmail.com")
        self.assertEqual(otp.mask_email("a@x.co"), "a***@x.co")

    @override_settings(DEBUG=True)
    def test_issue_otp_without_email_fails_cleanly(self):
        """Accounts created without an email must fail with a clear message
        instead of a cryptic SMTPRecipientsRefused with an empty recipient."""
        no_email_user = User.objects.create_user(username="noemail")
        result = otp.issue_otp(no_email_user)
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["sent"])
        self.assertIn("no email address", result["message"])
        # No code/state was written for the doomed send.
        record = EmailVerification.objects.get(user=no_email_user)
        self.assertEqual(record.otp_hash, "")
        self.assertIsNone(record.otp_last_sent_at)

    def test_issue_otp_without_email_generic_message_in_prod(self):
        """Outside DEBUG the reason stays generic (no internals leaked)."""
        no_email_user = User.objects.create_user(username="noemail2")
        result = otp.issue_otp(no_email_user)
        self.assertEqual(result["status"], "error")
        self.assertEqual(
            result["message"],
            "We couldn't send the email right now. Please try again in a moment.",
        )


class SignupOTPFlowTest(TestCase):
    """Manual signup > OTP screen > verification > dashboard."""

    def setUp(self):
        patcher = mock.patch(SEND_PATH, return_value=(True, ""))
        patcher.start()
        self.addCleanup(patcher.stop)
        # signup.html renders {% provider_login_url 'google' %}, which needs
        # a Google SocialApp in the (fresh) test database.
        from allauth.socialaccount.models import SocialApp
        from django.contrib.sites.models import Site
        app = SocialApp.objects.create(
            provider="google", name="Google", client_id="test", secret="test"
        )
        app.sites.add(Site.objects.get_current())

    def _signup(self):
        return self.client.post(reverse("accounts:signup"), {
            "username": "priya",
            "email": "priya@example.com",
            "password": "Test@12345",
            "confirm_password": "Test@12345",
        })

    def _post_json(self, url, payload):
        import json as _json
        return self.client.post(
            url, data=_json.dumps(payload), content_type="application/json",
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
        )

    def test_signup_redirects_to_otp_screen(self):
        resp = self._signup()
        self.assertRedirects(resp, reverse("accounts:verify_otp"))
        user = User.objects.get(username="priya")
        record = EmailVerification.objects.get(user=user)
        self.assertFalse(record.is_verified)
        self.assertTrue(record.otp_hash)  # a code was issued (hashed)

    def test_signup_does_not_log_user_in(self):
        self._signup()
        session = self.client.session
        self.assertNotIn("_auth_user_id", session)
        self.assertIn(otp.OTP_SESSION_KEY, session)

    def test_signup_duplicate_email_rejected(self):
        User.objects.create_user(username="other", email="PRIYA@example.com", password="x")
        resp = self._signup()
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "already exists")
        self.assertEqual(User.objects.filter(email__iexact="priya@example.com").count(), 1)

    def test_full_verify_flow_reaches_dashboard(self):
        self._signup()
        user = User.objects.get(username="priya")
        code = otp.generate_otp()
        record = EmailVerification.objects.get(user=user)
        record.otp_hash = otp.hash_otp(code)
        record.otp_expiry = timezone.now() + datetime.timedelta(minutes=5)
        record.save()

        resp = self._post_json(reverse("accounts:verify_otp"), {"otp": code})
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["redirect"], "/dashboard/")

        user.refresh_from_db()
        record.refresh_from_db()
        self.assertTrue(record.is_verified)
        # User is authenticated and lands on the dashboard.
        page = self.client.get(reverse("dashboard:index"))
        self.assertEqual(page.status_code, 200)

    def test_verify_wrong_code_shows_error(self):
        self._signup()
        resp = self._post_json(reverse("accounts:verify_otp"), {"otp": "000000"})
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["status"], "invalid")
        self.assertEqual(data["attempts_left"], otp.OTP_MAX_ATTEMPTS - 1)

    def test_expired_otp_message(self):
        self._signup()
        user = User.objects.get(username="priya")
        code = otp.generate_otp()
        record = EmailVerification.objects.get(user=user)
        record.otp_hash = otp.hash_otp(code)
        record.otp_expiry = timezone.now() - datetime.timedelta(seconds=1)
        record.save()

        resp = self._post_json(reverse("accounts:verify_otp"), {"otp": code})
        self.assertEqual(resp.json()["status"], "expired")

    def test_resend_endpoint_respects_cooldown(self):
        self._signup()  # signup just sent a code -> cooldown is active
        url = reverse("accounts:resend_otp")
        headers = {"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}
        first = self.client.post(url, headers=headers)
        self.assertEqual(first.status_code, 429)  # cooldown active

        # Simulate the 60s wait, then the resend succeeds.
        user = User.objects.get(username="priya")
        record = EmailVerification.objects.get(user=user)
        record.otp_last_sent_at = timezone.now() - datetime.timedelta(seconds=61)
        record.save()
        old_hash = record.otp_hash

        second = self.client.post(url, headers=headers)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["success"])
        record.refresh_from_db()
        self.assertNotEqual(record.otp_hash, old_hash)  # old code invalidated

    def test_otp_page_never_leaks_the_code(self):
        self._signup()
        resp = self.client.get(reverse("accounts:verify_otp"))
        self.assertEqual(resp.status_code, 200)
        record = EmailVerification.objects.get(user__username="priya")
        self.assertNotIn(record.otp_hash, resp.content.decode())

    @override_settings(DEBUG=True)
    def test_signup_without_email_rejected(self):
        """Email is mandatory now — blank-email accounts would be unable to
        receive their OTP (Gmail 555 syntax error on empty recipient)."""
        resp = self.client.post(reverse("accounts:signup"), {
            "username": "noemailuser",
            "email": "",
            "password": "Test@12345",
            "confirm_password": "Test@12345",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="noemailuser").exists())

    def test_send_failure_is_shown_on_the_page(self):
        """A failed SMTP send must surface in the UI, never fail silently."""
        with mock.patch(SEND_PATH, return_value=(False, "smtp down for maintenance")):
            self._signup()  # issue fails, but signup still redirects
            resp = self.client.get(reverse("accounts:verify_otp"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "smtp down for maintenance")

    @override_settings(DEBUG=True)
    def test_dev_code_banner_in_debug(self):
        """DEBUG convenience: the plain code is on the page so the flow is
        testable even when Gmail filters the email."""
        self._signup()
        self.assertIn("otp_dev_code", self.client.session)
        resp = self.client.get(reverse("accounts:verify_otp"))
        self.assertContains(resp, "Development mode")
        session_code = self.client.session["otp_dev_code"]
        self.assertContains(resp, session_code)

    @override_settings(DEBUG=True)
    def test_dev_code_cleared_after_successful_verify(self):
        self._signup()
        user = User.objects.get(username="priya")
        code = self.client.session["otp_dev_code"]
        record = EmailVerification.objects.get(user=user)
        record.otp_hash = otp.hash_otp(code)
        record.otp_expiry = timezone.now() + datetime.timedelta(minutes=5)
        record.save()

        self._post_json(reverse("accounts:verify_otp"), {"otp": code})
        self.assertNotIn("otp_dev_code", self.client.session)

    def test_no_dev_code_when_debug_off(self):
        """Production safety: no plain code is stored or rendered."""
        self._signup()
        self.assertNotIn("otp_dev_code", self.client.session)
        resp = self.client.get(reverse("accounts:verify_otp"))
        self.assertNotContains(resp, "Development mode")


class LoginOTPFlowTest(TestCase):
    """Login behaviour for verified / unverified accounts."""

    def setUp(self):
        patcher = mock.patch(SEND_PATH, return_value=(True, ""))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _make_user(self, verified=True, with_record=True):
        user = User.objects.create_user(
            username="rahul", email="rahul@example.com", password="Test@12345"
        )
        if with_record:
            record = otp.get_or_create_record(user)
            record.is_verified = verified
            record.save()
        return user

    def test_verified_user_logs_in_without_otp(self):
        self._make_user(verified=True)
        resp = self.client.post(reverse("accounts:login"), {
            "username": "rahul", "password": "Test@12345",
        })
        self.assertRedirects(resp, reverse("dashboard:index"))

    def test_unverified_user_is_sent_to_otp_screen(self):
        self._make_user(verified=False)
        resp = self.client.post(reverse("accounts:login"), {
            "username": "rahul", "password": "Test@12345",
        })
        self.assertRedirects(resp, reverse("accounts:verify_otp"))
        # Not fully logged in - session-bound to the OTP screen instead.
        self.assertIn(otp.OTP_SESSION_KEY, self.client.session)

    def test_user_without_record_logs_in_without_otp(self):
        self._make_user(with_record=False)
        resp = self.client.post(reverse("accounts:login"), {
            "username": "rahul", "password": "Test@12345",
        })
        self.assertRedirects(resp, reverse("dashboard:index"))


class SocialSignupOTPTest(TestCase):
    """Google signups get an OTP issued via the user_signed_up signal."""

    def setUp(self):
        patcher = mock.patch(SEND_PATH, return_value=(True, ""))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.factory = RequestFactory()

    def test_social_signup_issues_otp(self):
        from allauth.account.signals import user_signed_up

        user = User.objects.create_user(username="goog", email="goog@gmail.com", password="x")
        request = self.factory.get("/")
        request.session = {}

        with mock.patch(SEND_PATH, return_value=(True, "")) as send:
            user_signed_up.send(sender=User, request=request, user=user, sociallogin=object())

        self.assertTrue(send.called)
        record = EmailVerification.objects.get(user=user)
        self.assertFalse(record.is_verified)
        self.assertEqual(request.session.get(otp.OTP_SESSION_KEY), user.id)

    def test_manual_signup_does_not_double_send(self):
        from allauth.account.signals import user_signed_up

        user = User.objects.create_user(username="man", email="man@example.com", password="x")
        request = self.factory.get("/")
        request.session = {}

        with mock.patch(SEND_PATH, return_value=(True, "")) as send:
            user_signed_up.send(sender=User, request=request, user=user, sociallogin=None)
        self.assertFalse(send.called)  # signup_view handles it

    def test_email_required_config(self):
        """OTP needs a real address — social auto-signup must never create
        an email-less user (that left accounts stuck with Gmail 555 errors)."""
        from django.conf import settings
        self.assertTrue(settings.ACCOUNT_EMAIL_REQUIRED)
        self.assertEqual(settings.ACCOUNT_EMAIL_VERIFICATION, "none")

    def test_emailless_social_login_goes_to_signup_form(self):
        """Verify allauth's own auto-signup logic: with email required and no
        email provided by the provider, auto-signup is blocked (the user is
        sent to the email-collection form instead of creating a broken user)."""
        import types
        from allauth.socialaccount.internal.flows import signup as signup_flow

        request = self.factory.get("/")
        no_email_login = types.SimpleNamespace(email_addresses=[])

        auto_signup, resp = signup_flow.process_auto_signup_email(request, no_email_login)
        self.assertFalse(auto_signup)
        self.assertIsNone(resp)