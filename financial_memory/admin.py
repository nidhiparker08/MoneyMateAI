from django.contrib import admin

from .models import MemoryEntry, MerchantAlias, RecurringPattern, ReviewQueueItem


@admin.register(MemoryEntry)
class MemoryEntryAdmin(admin.ModelAdmin):
    list_display = (
        "signal_key", "entity_type", "entity_value", "user",
        "confidence", "hit_count", "correction_count", "is_active",
        "updated_at",
    )
    list_filter = ("entity_type", "signal_type", "is_active")
    search_fields = ("signal_key", "raw_signal", "entity_value", "user__username")
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at", "hit_count", "correction_count", "last_matched_at")


@admin.register(MerchantAlias)
class MerchantAliasAdmin(admin.ModelAdmin):
    list_display = ("alias", "canonical_name", "user", "hit_count", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("alias", "canonical_name", "user__username")


@admin.register(RecurringPattern)
class RecurringPatternAdmin(admin.ModelAdmin):
    list_display = (
        "label", "pattern_type", "frequency", "avg_amount",
        "occurrences_count", "last_occurrence", "next_expected",
        "confidence", "is_active", "user",
    )
    list_filter = ("pattern_type", "frequency", "is_active")
    search_fields = ("label", "merchant_key", "user__username")


@admin.register(ReviewQueueItem)
class ReviewQueueItemAdmin(admin.ModelAdmin):
    list_display = (
        "original_description", "merchant_guess", "suggested_category",
        "amount", "transaction_type", "status", "source", "user", "created_at",
    )
    list_filter = ("status", "source", "transaction_type")
    search_fields = ("original_description", "merchant_guess", "user__username")
