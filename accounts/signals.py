"""
Auth signals.

Handles the Google (social) signup path: when allauth creates a brand-new
user via a social provider, issue an OTP immediately. Manual signups do
this inside signup_view instead (the ``sociallogin`` kwarg is None there).
"""

from django.contrib.auth import get_user_model
from django.dispatch import receiver
from allauth.account.signals import user_signed_up

from . import otp

User = get_user_model()


@receiver(user_signed_up, sender=User)
def send_otp_on_social_signup(sender, request, user, sociallogin=None, **kwargs):
    if sociallogin is None:
        return  # manual signup — handled by accounts.views.signup_view

    record = otp.get_or_create_record(user)
    if not record.is_verified:
        otp.issue_otp(user, record)
        if request is not None:
            request.session[otp.OTP_SESSION_KEY] = user.id