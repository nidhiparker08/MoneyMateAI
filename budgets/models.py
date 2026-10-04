from django.conf import settings
from django.db import models

from transactions.models import TransactionCategory


class Budget(models.Model):

    MONTH_CHOICES = [
        (1, "January"),
        (2, "February"),
        (3, "March"),
        (4, "April"),
        (5, "May"),
        (6, "June"),
        (7, "July"),
        (8, "August"),
        (9, "September"),
        (10, "October"),
        (11, "November"),
        (12, "December"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets",
    )

    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.CASCADE,
        related_name="budgets",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    month = models.PositiveSmallIntegerField(
        choices=MONTH_CHOICES,
    )

    year = models.PositiveIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = ["-year", "-month"]

        unique_together = (
            "user",
            "category",
            "month",
            "year",
        )

    def __str__(self):

        return (
            f"{self.category.name} "
            f"{self.month}/{self.year}"
        )