"""
Email-verification gate.

Authenticated users who have not verified their email (i.e. they have an
EmailVerification row with is_verified=False) are kept on the OTP screen
until they verify. Users without a verification row are unaffected, so
existing accounts and the whole Google login flow keep working as before.
"""

from django.shortcuts import redirect

from . import otp

EXEMPT_PREFIXES = (
    "/accounts/verify",   # OTP screen + resend endpoint
    "/accounts/logout/",  # must stay reachable
    "/admin/",            # staff tooling
    "/static/",
    "/media/",
)


class EmailVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and not otp.is_email_verified(user)
            and not request.path.startswith(EXEMPT_PREFIXES)
        ):
            request.session[otp.OTP_SESSION_KEY] = user.id
            return redirect("accounts:verify_otp")
        return self.get_response(request)