from django.db import models
from django.contrib.auth.models import User


class ReportHistory(models.Model):

    REPORT_TYPES = (
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("halfyear", "Half Year"),
        ("year", "Year"),
        ("custom", "Custom"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="report_history",
    )

    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPES,
    )

    generated_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.user.username} - {self.report_type}"