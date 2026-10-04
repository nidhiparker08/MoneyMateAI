from django.contrib import admin

from .models import (
    TransactionCategory,
    Transaction,
)


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "category_type",
        "is_default",
        "user",
    )

    list_filter = (
        "category_type",
        "is_default",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "category_type",
        "name",
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "merchant",
        "transaction_type",
        "amount",
        "category",
        "payment_method",
        "import_source",
        "transaction_date",
        "user",
    )

    list_filter = (
        "transaction_type",
        "payment_method",
        "import_source",
        "transaction_date",
    )

    search_fields = (
        "title",
        "merchant",
        "notes",
    )

    ordering = (
        "-transaction_date",
    )

    date_hierarchy = "transaction_date"