"""Management command: detect recurring transaction patterns for all users.

Usage::

    python manage.py detect_recurring_patterns              # all users
    python manage.py detect_recurring_patterns --user alice # single user
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from financial_memory.services import RecurringDetector


class Command(BaseCommand):
    help = "Detect recurring transactions and store them as RecurringPattern rows."

    def add_arguments(self, parser):
        parser.add_argument("--user", help="Restrict to a specific username.")

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()
        if options.get("user"):
            users = users.filter(username=options["user"])

        total = 0
        for user in users:
            patterns = RecurringDetector.detect_for_user(user)
            total += len(patterns)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{user.username}: {len(patterns)} recurring pattern(s) detected"
                )
            )
        self.stdout.write(self.style.SUCCESS(f"Done. Total: {total}"))
