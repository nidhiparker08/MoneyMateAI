from django.db import models
from django.conf import settings


class Goal(models.Model):

    GOAL_TYPES = [
        ("house", "House"),
        ("car", "Car"),
        ("bike", "Bike"),
        ("vacation", "Vacation"),
        ("education", "Education"),
        ("emergency", "Emergency Fund"),
        ("wedding", "Wedding"),
        ("laptop", "Laptop"),
        ("phone", "Phone"),
        ("custom", "Custom"),
    ]

    PRIORITIES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    STATUS = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("paused", "Paused"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goals"
    )

    title = models.CharField(max_length=120)

    goal_type = models.CharField(
        max_length=30,
        choices=GOAL_TYPES,
        default="custom"
    )

    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    current_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    deadline = models.DateField()

    priority = models.CharField(
        max_length=10,
        choices=PRIORITIES,
        default="medium"
    )

    status = models.CharField(
        max_length=12,
        choices=STATUS,
        default="active"
    )

    monthly_target = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = ["deadline"]

    def __str__(self):

        return self.title

    @property
    def progress_percentage(self):

        if self.target_amount == 0:
            return 0

        return round(
            (self.current_amount / self.target_amount) * 100,
            1
        )

    @property
    def remaining_amount(self):

        return self.target_amount - self.current_amount