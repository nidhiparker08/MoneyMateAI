from django.apps import AppConfig


class FinancialMemoryConfig(AppConfig):
    """Django app that hosts the Financial Memory Engine.

    The Financial Memory Engine is a per-user learning layer that observes how
    each individual manages money and remembers their corrections so future
    transactions can be classified automatically.

    All other apps (transactions, goals, investments, gmail_sync, ai, ...)
    should consume the memory via `financial_memory.services.memory_service`
    instead of duplicating classification / correction logic.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "financial_memory"
    verbose_name = "Financial Memory Engine"

    def ready(self):  # pragma: no cover - side effects only
        # Register signal handlers that keep the memory in sync with
        # user corrections on transactions.
        from . import signals  # noqa: F401
