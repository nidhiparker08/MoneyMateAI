from django.contrib import admin

from .models import AIMemory, MemoryExtractionLog


@admin.register(AIMemory)
class AIMemoryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "memory_type",
        "key",
        "importance",
        "confidence",
        "source",
        "updated_at",
    )

    list_filter = (
        "memory_type",
        "source",
        "importance",
    )

    search_fields = (
        "user__username",
        "key",
        "value",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_used",
        "last_verified",
    )

    ordering = (
        "-importance",
        "-updated_at",
    )

    list_per_page = 25


@admin.register(MemoryExtractionLog)
class MemoryExtractionLogAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "model_used",
        "processing_time_ms",
        "created_at",
    )

    list_filter = (
        "status",
        "model_used",
    )

    search_fields = (
        "user__username",
        "message",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 25