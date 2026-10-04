"""
Auto-generate notifications for domain events.

The philosophy is minimal: only surface things the user really cares about.
The one interactive notification is when a newly imported transaction lands
without a category — we ask the user to categorise so the AI Memory Engine
can learn it forever.
"""
from decimal import Decimal

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .services import notify


LARGE_TRANSACTION_THRESHOLD = Decimal("10000")  # ₹10k


@receiver(post_save, sender="transactions.Transaction")
def _transaction_post_save(sender, instance, created, **kwargs):
    if not created:
        return

    tx = instance
    user = getattr(tx, "user", None)
    if user is None:
        return

    # Ask the user to categorise if this is an imported transaction with no category.
    if tx.category_id is None and tx.import_source != "manual":
        notify(
            user,
            "uncategorised_transaction",
            title=f"Categorise “{tx.title[:40]}”",
            description=(
                f"₹{tx.amount:.0f} from {tx.import_source.upper()} import "
                f"needs a category so MoneyMate can remember it forever."
            ),
            action_url="/transactions/",
            action_label="Categorise",
            ref_type="transaction",
            ref_id=str(tx.id),
            priority="high",
        )

    # Large transaction alert
    if tx.transaction_type == "expense" and Decimal(str(tx.amount)) >= LARGE_TRANSACTION_THRESHOLD:
        notify(
            user,
            "large_transaction",
            title=f"Large expense: ₹{tx.amount:.0f}",
            description=(
                f"{tx.title} — a bigger-than-usual expense was recorded. "
                "Review to make sure it looks right."
            ),
            action_url="/transactions/",
            action_label="Review",
            ref_type="transaction",
            ref_id=str(tx.id),
            priority="normal",
        )


@receiver(post_save, sender="transactions.Transaction")
def _transaction_categorised(sender, instance, created, **kwargs):
    """Resolve any pending 'uncategorised_transaction' notification when a category is set."""
    if created:
        return
    tx = instance
    if tx.category_id is None:
        return

    from .models import Notification

    Notification.objects.filter(
        user=tx.user,
        notif_type="uncategorised_transaction",
        ref_type="transaction",
        ref_id=str(tx.id),
        is_resolved=False,
    ).update(is_resolved=True, is_read=True)


@receiver(post_delete, sender="transactions.Transaction")
def _transaction_deleted(sender, instance, **kwargs):
    from .models import Notification

    Notification.objects.filter(
        ref_type="transaction",
        ref_id=str(instance.id),
    ).delete()
