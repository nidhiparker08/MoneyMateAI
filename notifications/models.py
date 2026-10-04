from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    Central notification model that powers the bell dropdown and the
    dedicated /notifications/ page.

    A notification is either informational (shown & marked read) or
    actionable (e.g. requires the user to categorise an uncategorised
    transaction).  When an action is completed, the notification is
    marked resolved automatically.
    """

    CATEGORY_CHOICES = [
        ("bank", "Bank"),
        ("transaction", "Transaction"),
        ("budget", "Budget"),
        ("ai", "AI"),
        ("investment", "Investment"),
        ("system", "System"),
    ]

    TYPE_CHOICES = [
        # Bank
        ("bank_connected", "Bank Connected"),
        ("bank_synced", "Bank Synced"),
        ("bank_sync_failed", "Sync Failed"),
        # Transactions
        ("large_transaction", "Large Transaction"),
        ("suspicious_transaction", "Suspicious Transaction"),
        ("duplicate_transaction", "Duplicate Transaction"),
        ("uncategorised_transaction", "Uncategorised Transaction"),
        # Budgets
        ("budget_warning", "Budget Warning"),
        ("budget_exceeded", "Budget Exceeded"),
        # AI
        ("ai_savings", "Savings Suggestion"),
        ("ai_insight", "Spending Insight"),
        ("ai_tip", "Financial Tip"),
        # Investments
        ("portfolio_update", "Portfolio Update"),
        # System
        ("import_completed", "Import Completed"),
        ("import_failed", "Import Failed"),
        ("welcome", "Welcome"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="system",
    )
    notif_type = models.CharField(
        max_length=40,
        choices=TYPE_CHOICES,
        default="ai_tip",
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="normal",
    )

    icon = models.CharField(
        max_length=40,
        default="fa-bell",
        help_text="FontAwesome class without the 'fa-solid' prefix.",
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    # Optional link that opens when the user clicks the notification.
    action_url = models.CharField(max_length=300, blank=True)
    # Optional label for the primary action button (e.g. 'Categorise').
    action_label = models.CharField(max_length=60, blank=True)

    # Optional payload for actionable notifications (e.g. transaction id).
    ref_type = models.CharField(max_length=40, blank=True)
    ref_id = models.CharField(max_length=64, blank=True)

    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(
        default=False,
        help_text="True once any required action has been completed.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"[{self.category}] {self.title} ({self.user_id})"

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "type": self.notif_type,
            "priority": self.priority,
            "icon": self.icon,
            "title": self.title,
            "description": self.description,
            "action_url": self.action_url,
            "action_label": self.action_label,
            "ref_type": self.ref_type,
            "ref_id": self.ref_id,
            "is_read": self.is_read,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat(),
        }
