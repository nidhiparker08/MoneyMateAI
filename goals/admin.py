from django.contrib import admin
from .models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "goal_type",
        "target_amount",
        "current_amount",
        "progress_percentage",
        "deadline",
        "priority",
        "status",
    )

    list_filter = (
        "goal_type",
        "priority",
        "status",
    )

    search_fields = (
        "title",
    )

    ordering = (
        "deadline",
    )