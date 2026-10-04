"""Recurring-pattern detection.

Analyses a user's :class:`transactions.models.Transaction` history and
produces / updates :class:`financial_memory.models.RecurringPattern` rows
representing salaries, subscriptions, EMIs, SIP investments, utility bills,
recurring transfers, and insurance premiums.

Invoke either from a management command or ad-hoc from a view (the memory
engine calls this after every 20 new transactions to keep the store fresh).
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from django.db import transaction as db_transaction

from ..models import RecurringPattern
from .memory_service import normalise_signal


# Category-name -> pattern_type hints (case-insensitive contains).
_PATTERN_HINTS: list[tuple[str, str]] = [
    ("salary", "salary"),
    ("payroll", "salary"),
    ("emi", "emi"),
    ("loan", "emi"),
    ("insurance", "insurance"),
    ("premium", "insurance"),
    ("electricity", "utility"),
    ("water", "utility"),
    ("gas", "utility"),
    ("internet", "utility"),
    ("broadband", "utility"),
    ("recharge", "utility"),
    ("mutual fund", "investment"),
    ("sip", "investment"),
    ("netflix", "subscription"),
    ("spotify", "subscription"),
    ("prime", "subscription"),
    ("subscription", "subscription"),
]


def _guess_pattern_type(description: str, category_name: str) -> str:
    blob = f"{description} {category_name or ''}".lower()
    for needle, kind in _PATTERN_HINTS:
        if needle in blob:
            return kind
    return "other"


def _intervals(dates: list[date]) -> list[int]:
    dates = sorted(dates)
    return [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]


def _classify_frequency(intervals: list[int]) -> str:
    if not intervals:
        return "irregular"
    median = statistics.median(intervals)
    if 5 <= median <= 9:
        return "weekly"
    if 12 <= median <= 17:
        return "biweekly"
    if 25 <= median <= 35:
        return "monthly"
    if 80 <= median <= 100:
        return "quarterly"
    if 350 <= median <= 380:
        return "yearly"
    return "irregular"


class RecurringDetector:
    """Detect recurring transactions for a given user."""

    MIN_OCCURRENCES = 2       # need at least 2 occurrences to consider recurring
    LOOKBACK_DAYS = 365       # look at last one year of history

    @classmethod
    @db_transaction.atomic
    def detect_for_user(cls, user) -> list[RecurringPattern]:
        """Scan the user's transactions and upsert :class:`RecurringPattern`s."""
        from transactions.models import Transaction  # local import

        since = date.today() - timedelta(days=cls.LOOKBACK_DAYS)
        transactions = (
            Transaction.objects
            .filter(user=user, transaction_date__gte=since)
            .select_related("category")
        )

        groups: dict[str, list] = defaultdict(list)
        for tx in transactions:
            key_source = tx.merchant or tx.title
            key = normalise_signal(key_source)
            if not key:
                continue
            groups[key].append(tx)

        detected: list[RecurringPattern] = []
        for key, txs in groups.items():
            if len(txs) < cls.MIN_OCCURRENCES:
                continue
            amounts = [float(t.amount) for t in txs]
            avg_amount = round(sum(amounts) / len(amounts), 2)
            last_amount = amounts[0]
            dates = [t.transaction_date for t in txs]
            freq = _classify_frequency(_intervals(dates))
            if freq == "irregular" and len(txs) < 3:
                continue
            last_occ = max(dates)
            # Guess pattern type
            desc = txs[0].merchant or txs[0].title
            cat_name = txs[0].category.name if txs[0].category else ""
            ptype = _guess_pattern_type(desc, cat_name)
            # Basic confidence: more occurrences + tighter dispersion == higher
            spread = max(amounts) - min(amounts)
            dispersion_penalty = 0
            if avg_amount:
                dispersion_penalty = min(40, int((spread / avg_amount) * 40))
            confidence = max(30, min(99, 40 + len(txs) * 12 - dispersion_penalty))

            label = (txs[0].merchant or txs[0].title or key)[:200]
            day_of_month = None
            if freq in {"monthly", "quarterly", "yearly"}:
                days = [d.day for d in dates]
                day_of_month = int(round(sum(days) / len(days)))
            next_expected = None
            if freq == "monthly":
                # add ~30 days to last occurrence
                next_expected = last_occ + timedelta(days=30)
            elif freq == "weekly":
                next_expected = last_occ + timedelta(days=7)
            elif freq == "biweekly":
                next_expected = last_occ + timedelta(days=14)
            elif freq == "quarterly":
                next_expected = last_occ + timedelta(days=90)
            elif freq == "yearly":
                next_expected = last_occ + timedelta(days=365)

            pattern, _ = RecurringPattern.objects.update_or_create(
                user=user,
                pattern_type=ptype,
                merchant_key=key,
                defaults={
                    "label": label,
                    "frequency": freq,
                    "avg_amount": Decimal(str(avg_amount)),
                    "last_amount": Decimal(str(last_amount)),
                    "day_of_month": day_of_month,
                    "last_occurrence": last_occ,
                    "next_expected": next_expected,
                    "occurrences_count": len(txs),
                    "confidence": confidence,
                    "is_active": True,
                    "linked_category": txs[0].category,
                    "linked_goal": txs[0].goal,
                    "metadata": {
                        "sample_titles": list({t.title for t in txs[:3]}),
                    },
                },
            )
            detected.append(pattern)

        # Deactivate patterns whose last occurrence is now very old.
        stale_cutoff = date.today() - timedelta(days=180)
        RecurringPattern.objects.filter(
            user=user, last_occurrence__lt=stale_cutoff, is_active=True
        ).update(is_active=False)

        return detected

    @classmethod
    def count(cls, user) -> int:
        return RecurringPattern.objects.filter(user=user, is_active=True).count()

    @classmethod
    def top(cls, user, limit: int = 5) -> list[RecurringPattern]:
        return list(
            RecurringPattern.objects
            .filter(user=user, is_active=True)
            .order_by("-confidence", "-occurrences_count")[:limit]
        )
