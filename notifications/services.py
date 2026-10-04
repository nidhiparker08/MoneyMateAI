"""
Notification helper service.

Any other Django app can import `notify(user, ...)` to raise a notification.
It is idempotent for actionable notifications via (ref_type, ref_id) so we
never nag the user twice for the same transaction.
"""
from typing import Optional

from .models import Notification


ICON_MAP = {
    "bank_connected": "fa-link",
    "bank_synced": "fa-arrows-rotate",
    "bank_sync_failed": "fa-triangle-exclamation",
    "large_transaction": "fa-money-bill-trend-up",
    "suspicious_transaction": "fa-shield-halved",
    "duplicate_transaction": "fa-clone",
    "uncategorised_transaction": "fa-tag",
    "budget_warning": "fa-gauge-high",
    "budget_exceeded": "fa-triangle-exclamation",
    "ai_savings": "fa-piggy-bank",
    "ai_insight": "fa-lightbulb",
    "ai_tip": "fa-sparkles",
    "portfolio_update": "fa-chart-line",
    "import_completed": "fa-file-circle-check",
    "import_failed": "fa-file-circle-xmark",
    "welcome": "fa-hand-sparkles",
}

CATEGORY_MAP = {
    "bank_connected": "bank",
    "bank_synced": "bank",
    "bank_sync_failed": "bank",
    "large_transaction": "transaction",
    "suspicious_transaction": "transaction",
    "duplicate_transaction": "transaction",
    "uncategorised_transaction": "transaction",
    "budget_warning": "budget",
    "budget_exceeded": "budget",
    "ai_savings": "ai",
    "ai_insight": "ai",
    "ai_tip": "ai",
    "portfolio_update": "investment",
    "import_completed": "system",
    "import_failed": "system",
    "welcome": "system",
}


def notify(
    user,
    notif_type: str,
    title: str,
    description: str = "",
    *,
    action_url: str = "",
    action_label: str = "",
    ref_type: str = "",
    ref_id: Optional[str] = None,
    priority: str = "normal",
    dedupe: bool = True,
) -> Notification:
    """Create (or return existing, unresolved) notification."""

    ref_id = str(ref_id) if ref_id is not None else ""

    if dedupe and ref_type and ref_id:
        existing = (
            Notification.objects.filter(
                user=user,
                notif_type=notif_type,
                ref_type=ref_type,
                ref_id=ref_id,
                is_resolved=False,
            ).first()
        )
        if existing:
            return existing

    return Notification.objects.create(
        user=user,
        category=CATEGORY_MAP.get(notif_type, "system"),
        notif_type=notif_type,
        priority=priority,
        icon=ICON_MAP.get(notif_type, "fa-bell"),
        title=title,
        description=description,
        action_url=action_url,
        action_label=action_label,
        ref_type=ref_type,
        ref_id=ref_id,
    )


def unread_count(user) -> int:
    return Notification.objects.filter(user=user, is_read=False).count()


def latest_for_user(user, limit: int = 8):
    return list(
        Notification.objects.filter(user=user).order_by("-created_at")[:limit]
    )
