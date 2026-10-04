from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        # Signals live in models.py — importing them ensures they register.
        from . import models  # noqa: F401
        # OTP verification signal (Google/social signups).
        from . import signals  # noqa: F401
