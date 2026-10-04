from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "notif_type", "is_read", "is_resolved", "created_at")
    list_filter = ("category", "notif_type", "is_read", "is_resolved")
    search_fields = ("title", "description", "user__username")
    ordering = ("-created_at",)
