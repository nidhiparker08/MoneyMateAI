"""Financial Memory Engine — persistent models.

These models power a per-user learning layer that continuously observes how
each individual manages money.  Whenever the user classifies, corrects,
renames or links a transaction (to a goal / merchant / investment / friend
etc.), a memory entry is stored so the same signal is never asked twice.

All tables are user-scoped, indexed on the normalised signal key, and use a
JSON `metadata` column so new learning capabilities can be added later
without schema migrations.

Entity vocabulary
-----------------
Signal types describe *where* the learnt signal came from:
    merchant           — merchant name / raw description keyword
    upi_id             — a UPI VPA (user@bank)
    counter_party      — a friend / family / business account name
    narration_keyword  — a distinctive keyword within a bank narration
    account_hint       — an account nickname (e.g. "Bike Savings")

Entity types describe *what* the signal maps to:
    category, subcategory, merchant_alias, goal, holding, salary_source,
    investment_platform, savings_account, subscription, insurance, loan,
    emi, utility, transfer, friend, family, business, contact
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# Enumerations (kept as string constants so new options don't need migrations)
# ---------------------------------------------------------------------------

SIGNAL_TYPES = [
    ("merchant", "Merchant"),
    ("upi_id", "UPI ID"),
    ("counter_party", "Counter Party"),
    ("narration_keyword", "Narration Keyword"),
    ("account_hint", "Account Hint"),
    ("pattern", "Pattern"),
]

ENTITY_TYPES = [
    ("category", "Category"),
    ("subcategory", "Subcategory"),
    ("merchant_alias", "Merchant Alias"),
    ("goal", "Goal"),
    ("holding", "Investment Holding"),
    ("salary_source", "Salary Source"),
    ("investment_platform", "Investment Platform"),
    ("savings_account", "Savings Account"),
    ("subscription", "Subscription"),
    ("insurance", "Insurance Provider"),
    ("loan", "Loan Provider"),
    ("emi", "EMI"),
    ("utility", "Utility"),
    ("transfer", "Transfer"),
    ("friend", "Friend"),
    ("family", "Family"),
    ("business", "Business Contact"),
    ("contact", "Contact"),
]

TRANSACTION_TYPES = [
    ("", "Unknown"),
    ("income", "Income"),
    ("expense", "Expense"),
    ("transfer", "Transfer"),
    ("investment", "Investment"),
]

RECURRING_PATTERN_TYPES = [
    ("subscription", "Subscription"),
    ("salary", "Salary"),
    ("emi", "EMI / Loan"),
    ("utility", "Utility"),
    ("investment", "Investment / SIP"),
    ("transfer", "Transfer"),
    ("insurance", "Insurance"),
    ("other", "Other Recurring"),
]

RECURRING_FREQUENCIES = [
    ("weekly", "Weekly"),
    ("biweekly", "Bi-Weekly"),
    ("monthly", "Monthly"),
    ("quarterly", "Quarterly"),
    ("yearly", "Yearly"),
    ("irregular", "Irregular"),
]

REVIEW_STATUSES = [
    ("pending", "Pending"),
    ("reviewed", "Reviewed"),
    ("dismissed", "Dismissed"),
    ("auto_resolved", "Auto-Resolved"),
]

REVIEW_SOURCES = [
    ("manual", "Manual"),
    ("csv", "CSV Import"),
    ("excel", "Excel Import"),
    ("pdf", "PDF Import"),
    ("gmail", "Gmail Import"),
    ("sms", "SMS Parser"),
    ("other", "Other"),
]


# ---------------------------------------------------------------------------
# MemoryEntry — the central learning table
# ---------------------------------------------------------------------------

class MemoryEntry(models.Model):
    """One learnt mapping between a normalised signal and an entity value.

    Example rows for user Alice::

        signal_type=merchant  signal_key="groww"       entity_type=investment_platform  entity_value="Groww"
        signal_type=merchant  signal_key="groww"       entity_type=category             linked_category=<Investments>
        signal_type=merchant  signal_key="abc pvt ltd" entity_type=salary_source        entity_value="ABC Pvt Ltd"
        signal_type=merchant  signal_key="rahul"       entity_type=friend               entity_value="Rahul"
        signal_type=account_hint signal_key="bike"     entity_type=goal                 linked_goal=<Bike Savings>
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memory_entries",
    )

    signal_type = models.CharField(max_length=32, choices=SIGNAL_TYPES, default="merchant")
    signal_key = models.CharField(max_length=255, db_index=True)
    raw_signal = models.CharField(max_length=500, blank=True)

    entity_type = models.CharField(max_length=32, choices=ENTITY_TYPES)
    entity_value = models.CharField(max_length=255, blank=True)

    # Optional strong FK links — resolved lazily via string references to avoid
    # circular imports.  Nullable because a memory can be about a name-only
    # entity (e.g. "Rahul") without a corresponding row.
    linked_category = models.ForeignKey(
        "transactions.TransactionCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memory_entries",
    )
    linked_goal = models.ForeignKey(
        "goals.Goal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memory_entries",
    )
    linked_holding = models.ForeignKey(
        "investments.Holding",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memory_entries",
    )

    # Optional "shape" of the transaction — learnt sub-classification.
    transaction_type = models.CharField(max_length=16, choices=TRANSACTION_TYPES, blank=True, default="")
    subcategory = models.CharField(max_length=100, blank=True)

    # Confidence / usage bookkeeping.
    confidence = models.PositiveSmallIntegerField(default=100)
    hit_count = models.PositiveIntegerField(default=0)
    correction_count = models.PositiveIntegerField(default=1)
    last_matched_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    # Freeform JSON bag for future learning attributes (average amount,
    # preferred payment method, recurring hints, etc.) — keeps the schema
    # future-proof without additional migrations.
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Memory Entry"
        verbose_name_plural = "Memory Entries"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "signal_type", "signal_key", "entity_type"],
                name="unique_memory_signal_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["user", "signal_key"]),
            models.Index(fields=["user", "entity_type"]),
        ]

    def __str__(self):  # pragma: no cover - trivial
        return f"{self.signal_key} → {self.entity_type}:{self.entity_value or self.linked_category or self.linked_goal}"


# ---------------------------------------------------------------------------
# MerchantAlias — many-to-one merchant normalisation
# ---------------------------------------------------------------------------

class MerchantAlias(models.Model):
    """Alternative spellings that all resolve to a single canonical merchant.

    Bank statements produce noisy strings like ``AMAZON PAY INDIA``,
    ``AMZN*MKTP``, ``AMAZONFRESH BLR`` — all of which the user probably wants
    treated as ``Amazon``.  A single :class:`MemoryEntry` may back several
    aliases.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merchant_aliases",
        null=True,
        blank=True,
    )
    alias = models.CharField(max_length=255, db_index=True)
    canonical_name = models.CharField(max_length=255)

    linked_memory = models.ForeignKey(
        MemoryEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="aliases",
    )

    hit_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["canonical_name", "alias"]
        verbose_name = "Merchant Alias"
        verbose_name_plural = "Merchant Aliases"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "alias"],
                name="unique_alias_per_user",
            )
        ]

    def __str__(self):  # pragma: no cover
        return f"{self.alias} → {self.canonical_name}"


# ---------------------------------------------------------------------------
# RecurringPattern — detected periodic transactions
# ---------------------------------------------------------------------------

class RecurringPattern(models.Model):
    """Detected recurring transactions (salary, subscriptions, EMI, SIPs, …).

    Built by the ``financial_memory.services.recurring_detector`` service on
    demand or via the ``detect_recurring_patterns`` management command.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_patterns",
    )

    pattern_type = models.CharField(max_length=32, choices=RECURRING_PATTERN_TYPES, default="subscription")
    label = models.CharField(max_length=200)
    merchant_key = models.CharField(max_length=255, db_index=True)
    frequency = models.CharField(max_length=16, choices=RECURRING_FREQUENCIES, default="monthly")

    avg_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    day_of_month = models.PositiveSmallIntegerField(null=True, blank=True)
    last_occurrence = models.DateField(null=True, blank=True)
    next_expected = models.DateField(null=True, blank=True)
    occurrences_count = models.PositiveIntegerField(default=0)
    confidence = models.PositiveSmallIntegerField(default=50)

    linked_category = models.ForeignKey(
        "transactions.TransactionCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_patterns",
    )
    linked_goal = models.ForeignKey(
        "goals.Goal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_patterns",
    )
    linked_holding = models.ForeignKey(
        "investments.Holding",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_patterns",
    )

    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Recurring Pattern"
        verbose_name_plural = "Recurring Patterns"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "pattern_type", "merchant_key"],
                name="unique_recurring_per_user",
            )
        ]

    def __str__(self):  # pragma: no cover
        return f"{self.label} ({self.frequency})"


# ---------------------------------------------------------------------------
# ReviewQueueItem — items awaiting user classification
# ---------------------------------------------------------------------------

class ReviewQueueItem(models.Model):
    """Low-confidence / unknown transactions parked for later user review.

    We deliberately store the *raw* signal (description / merchant / amount)
    even if the associated :class:`Transaction` still exists, so the queue
    remains useful even if the transaction is deleted or re-imported.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_queue_items",
    )

    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_items",
    )

    original_description = models.CharField(max_length=500)
    merchant_guess = models.CharField(max_length=255, blank=True)
    suggested_category = models.CharField(max_length=100, blank=True)
    suggested_entity_type = models.CharField(max_length=32, choices=ENTITY_TYPES, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transaction_type = models.CharField(max_length=16, choices=TRANSACTION_TYPES, blank=True, default="")
    transaction_date = models.DateField(null=True, blank=True)

    confidence = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=16, choices=REVIEW_STATUSES, default="pending", db_index=True)
    source = models.CharField(max_length=16, choices=REVIEW_SOURCES, default="manual")

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Review Queue Item"
        verbose_name_plural = "Review Queue Items"
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):  # pragma: no cover
        return f"{self.original_description[:40]} — {self.status}"
