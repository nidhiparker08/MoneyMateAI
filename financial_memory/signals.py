"""Signal wiring for the Financial Memory Engine.

We keep this file intentionally tiny so any other app can safely import
``financial_memory`` at Django-boot time (via `apps.ready()`) without pulling
circular dependencies.  All heavy imports happen lazily inside the handlers.
"""
from __future__ import annotations

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(
    post_save,
    sender="transactions.Transaction",
    dispatch_uid="fm_remember_from_transaction",
)
def _remember_from_transaction(sender, instance, created, **kwargs):
    """
    Learn from manual transactions immediately.

    Imported transactions (BankHub/PDF/CSV/Excel/Gmail) are learned
    AFTER the import completes inside the importer.
    """

    # Invalid transaction
    if not instance or not getattr(instance, "user_id", None):
        return

    # Prevent recursion
    if getattr(instance, "_from_memory_service", False):
        return

    # Skip imported transactions.
    # They will be processed in bulk after the import finishes.
    if getattr(instance, "import_source", None):
        return

    from .services import memory_service

    memory_service.remember_correction(instance)


@receiver(post_delete, sender="transactions.Transaction", dispatch_uid="fm_cleanup_review_on_delete")
def _cleanup_review_on_delete(sender, instance, **kwargs):
    """When a transaction is deleted, dismiss any linked review items."""
    from .models import ReviewQueueItem
    ReviewQueueItem.objects.filter(transaction=instance).update(
        status="dismissed", transaction=None
    )
