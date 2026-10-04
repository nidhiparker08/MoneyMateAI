from django.contrib import admin

from .models import EmailVerification


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user", "is_verified", "verified_at",
        "otp_last_sent_at", "otp_attempts",
    )
    list_filter = ("is_verified",)
    search_fields = ("user__username", "user__email")
    readonly_fields = (
        "otp_hash", "otp_expiry", "otp_attempts", "otp_last_sent_at",
        "verified_at", "created_at", "updated_at",
    )
