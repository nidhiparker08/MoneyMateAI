from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from goals.models import Goal


class TransactionCategory(models.Model):

    CATEGORY_TYPES = (
        ("income", "Income"),
        ("expense", "Expense"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=50)

    category_type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPES,
    )

    color = models.CharField(
        max_length=20,
        default="#8B5CF6",
    )

    icon = models.CharField(
        max_length=50,
        default="fa-tag",
    )

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = ["name"]

        verbose_name = "Transaction Category"

        verbose_name_plural = "Transaction Categories"

    def __str__(self):

        return self.name


class Transaction(models.Model):

    TRANSACTION_TYPES = (
        ("income", "Income"),
        ("expense", "Expense"),
    )

    PAYMENT_METHODS = (
        ("cash", "Cash"),
        ("upi", "UPI"),
        ("debit_card", "Debit Card"),
        ("credit_card", "Credit Card"),
        ("net_banking", "Net Banking"),
        ("cheque", "Cheque"),
        ("other", "Other"),
    )

    IMPORT_SOURCES = (
        ("manual", "Manual"),
        ("csv", "CSV"),
        ("excel", "Excel"),
        ("pdf", "PDF"),
        ("gmail", "Gmail"),
        ("bankhub", "BankHub"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )

    goal = models.ForeignKey(
        Goal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contributions",
    )

    title = models.CharField(
        max_length=200,
    )

    merchant = models.CharField(
        max_length=200,
        blank=True,
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHODS,
        default="upi",
    )

    import_source = models.CharField(
        max_length=20,
        choices=IMPORT_SOURCES,
        default="manual",
    )

    transaction_date = models.DateField()

    transaction_time = models.TimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    # ------------------------------------------------------------
    # Transaction Intelligence Layer — enrichment fields.
    # All optional and non-breaking; populated by TransactionIntelligence.
    # ------------------------------------------------------------

    transaction_type_detail = models.CharField(
        max_length=32,
        blank=True,
        db_index=True,
        help_text=(
            "Fine-grained type: salary, investment, goal_contribution, "
            "insurance, loan_emi, subscription, utility_bill, cashback, "
            "refund, interest, dividend, tax, internal_transfer, "
            "friend_transfer, business_transfer, income, expense."
        ),
    )

    subcategory = models.CharField(
        max_length=64,
        blank=True,
    )

    receiver = models.CharField(
        max_length=120,
        blank=True,
    )

    confidence_score = models.PositiveSmallIntegerField(
        default=0,
        help_text="0-100 confidence assigned by TransactionIntelligence.",
    )

    intelligence_source = models.CharField(
        max_length=24,
        blank=True,
        help_text="memory | rules | regex | dictionary | pattern | default | manual",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            "-transaction_date",
            "-created_at",
        ]

    def __str__(self):

        if self.goal:

            return f"{self.title} → {self.goal.title}"

        return f"{self.title} - ₹{self.amount}"