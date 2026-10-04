from django.conf import settings
from django.db import models


class MemoryType(models.TextChoices):
    GOAL = "goal", "Goal"
    PREFERENCE = "preference", "Preference"
    RISK = "risk", "Risk Profile"
    INVESTMENT = "investment", "Investment"
    FINANCIAL = "financial", "Financial"
    LIFESTYLE = "lifestyle", "Lifestyle"
    PERSONAL = "personal", "Personal"
    COMMUNICATION = "communication", "Communication"


class AIMemory(models.Model):
    """
    Stores long-term memories learned by the AI.

    These memories persist across conversations and are used
    to personalise future responses.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_memories",
    )

    memory_type = models.CharField(
        max_length=30,
        choices=MemoryType.choices,
        db_index=True,
    )

    key = models.CharField(
        max_length=100,
        db_index=True,
    )

    value = models.JSONField()

    confidence = models.PositiveSmallIntegerField(
        default=100,
    )

    importance = models.PositiveSmallIntegerField(
        default=5,
    )

    source = models.CharField(
        max_length=50,
        default="conversation",
    )

    last_used = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_verified = models.DateTimeField(
        null=True,
        blank=True,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-importance", "-updated_at"]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "memory_type",
                ]
            ),
            models.Index(
                fields=[
                    "user",
                    "key",
                ]
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "memory_type",
                    "key",
                ],
                name="unique_ai_memory",
            )
        ]

    def __str__(self):
        return (
            f"{self.user.username} | "
            f"{self.memory_type} | "
            f"{self.key}"
        )

class MemoryExtractionLog(models.Model):
    """
    Stores every memory extraction attempt made by the AI.

    Useful for debugging, improving prompts,
    and auditing what the AI learned.
    """

    STATUS_CHOICES = [
        ("accepted", "Accepted"),
        ("updated", "Updated"),
        ("ignored", "Ignored"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memory_logs",
    )

    message = models.TextField()

    extracted_memory = models.JSONField(
        default=dict,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="accepted",
    )

    model_used = models.CharField(
        max_length=50,
        default="gemini-3.6-flash",
    )

    processing_time_ms = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user.username} | "
            f"{self.status} | "
            f"{self.created_at:%d-%m-%Y %H:%M}"
        )