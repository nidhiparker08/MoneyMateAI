"""MemoryService — the single entry-point used across the project.

All other modules (transactions, goals, investments, gmail_sync, ai, …)
should call into this service instead of duplicating business logic.

Design notes
------------
* Every mutation goes through :meth:`MemoryService.remember`, so we always
  keep hit / correction counters up to date.
* Reads go through :meth:`MemoryService.match` and :meth:`classify`.  These
  are safe to call on every transaction: they touch a single indexed table
  (`financial_memory_memoryentry`) filtered by ``user`` and ``signal_key``.
* All heavy imports (transactions, goals, investments, RapidFuzz) are
  performed lazily inside methods so this module can be imported early
  during Django app loading without triggering circular imports.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from django.db import transaction as db_transaction
from django.db.models import Q
from django.utils import timezone
from django.db import transaction

from ..models import (
    ENTITY_TYPES,
    MemoryEntry,
    MerchantAlias,
    RECURRING_PATTERN_TYPES,
    ReviewQueueItem,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

_NOISE_TOKENS = {
    "upi", "upi-", "upi/", "upi:", "imps", "neft", "rtgs", "pos",
    "atm", "txn", "ref", "payment", "transfer", "credited",
    "debited", "by", "to", "from", "india", "pvt", "ltd",
    "private", "limited", "paytm", "phonepe", "gpay", "bhim",
}


def normalise_signal(text: str) -> str:
    """Return a lowercase, alphanumeric key suitable for indexed lookup.

    * Lowercases everything.
    * Removes punctuation and long digit runs.
    * Drops common banking noise words (UPI, IMPS, POS, TXN…).
    * Collapses whitespace.

    The result is deterministic so it can safely be used as a DB unique-key.
    """
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r"[^\w\s@\.]", " ", text)  # keep @ and . for UPI ids
    text = re.sub(r"\d{4,}", " ", text)          # drop long numbers (txn ids)
    tokens = [t for t in text.split() if t and t not in _NOISE_TOKENS]
    return re.sub(r"\s+", " ", " ".join(tokens)).strip()


def _extract_upi_id(text: str) -> str | None:
    """Return a UPI VPA (like ``user@bank``) if present in ``text``."""
    if not text:
        return None
    match = re.search(r"[\w\.\-]+@[\w\.\-]+", text.lower())
    if match and "." not in match.group(0).split("@")[-1][:2]:
        # rough sanity check to avoid matching plain emails, though UPI ids
        # look almost identical — keep them all, they're valid signals.
        pass
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# Dataclass returned by classify()
# ---------------------------------------------------------------------------


@dataclass
class ClassificationResult:
    """What the memory thinks a raw description means."""

    merchant: str = ""
    category: str = ""
    subcategory: str = ""
    transaction_type: str = ""
    confidence: int = 0
    source: str = "unknown"          # memory / alias / static / fallback
    linked_category_id: int | None = None
    linked_goal_id: int | None = None
    linked_holding_id: int | None = None
    entity_hits: dict[str, Any] = field(default_factory=dict)
    memory_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "merchant": self.merchant,
            "category": self.category,
            "subcategory": self.subcategory,
            "transaction_type": self.transaction_type,
            "confidence": self.confidence,
            "source": self.source,
            "linked_category_id": self.linked_category_id,
            "linked_goal_id": self.linked_goal_id,
            "linked_holding_id": self.linked_holding_id,
            "entity_hits": self.entity_hits,
            "memory_ids": self.memory_ids,
        }


# ---------------------------------------------------------------------------
# MemoryService — the singleton facade used everywhere
# ---------------------------------------------------------------------------


class MemoryService:
    """Public API for the Financial Memory Engine.

    Instantiate via the module-level singleton ``memory_service``.
    Every method is stateless — the class exists purely for logical grouping.
    """

    # ---- WRITE PATH ------------------------------------------------------

    @db_transaction.atomic
    def remember(
        self,
        *,
        user,
        signal_key: str,
        entity_type: str,
        entity_value: str = "",
        signal_type: str = "merchant",
        raw_signal: str = "",
        subcategory: str = "",
        transaction_type: str = "",
        linked_category=None,
        linked_goal=None,
        linked_holding=None,
        confidence: int = 100,
        metadata: dict | None = None,
    ) -> MemoryEntry | None:
        """Upsert a single (signal, entity) mapping for ``user``.

        Returns the created / updated :class:`MemoryEntry` or ``None`` if the
        inputs were empty.
        """
        if not user or not user.is_authenticated:
            return None

        key = normalise_signal(signal_key)
        if not key or not entity_type:
            return None

        defaults = {
            "raw_signal": (raw_signal or signal_key)[:500],
            "entity_value": entity_value[:255],
            "subcategory": subcategory[:100],
            "transaction_type": transaction_type or "",
            "linked_category": linked_category,
            "linked_goal": linked_goal,
            "linked_holding": linked_holding,
            "confidence": max(0, min(100, int(confidence))),
            "metadata": metadata or {},
            "is_active": True,
        }

        entry, created = MemoryEntry.objects.get_or_create(
            user=user,
            signal_type=signal_type,
            signal_key=key,
            entity_type=entity_type,
            defaults=defaults,
        )
        if not created:
            # Update most fields but keep hit counter behaviour.
            for field_name, value in defaults.items():
                # Merge dictionaries; overwrite scalars.
                if field_name == "metadata" and isinstance(value, dict):
                    merged = dict(entry.metadata or {})
                    merged.update(value)
                    entry.metadata = merged
                elif value not in (None, "", 0):
                    setattr(entry, field_name, value)
            entry.correction_count = (entry.correction_count or 0) + 1
            entry.is_active = True
            entry.save()
        return entry

    def remember_correction(self, transaction, previous_snapshot: dict | None = None) -> list[MemoryEntry]:
        """Turn a user-corrected :class:`Transaction` into memory entries.

        This is the primary write path: every time a user manually edits or
        creates a transaction we extract every classifiable signal from it
        and store the mapping.

        ``previous_snapshot`` is optional — if provided it lets us skip
        "remember" calls for fields that did not change.
        """
        if not transaction or not transaction.user:
            return []

        user = transaction.user
        description = (transaction.title or "") + " " + (transaction.merchant or "")
        description = description.strip()
        if not description:
            return []

        # ---- Candidate signal keys extracted from the transaction ----
        signal_candidates: list[tuple[str, str]] = []  # (signal_type, raw_text)
        if transaction.merchant:
            signal_candidates.append(("merchant", transaction.merchant))
        signal_candidates.append(("merchant", transaction.title))

        upi = _extract_upi_id(description)
        if upi:
            signal_candidates.append(("upi_id", upi))

        created: list[MemoryEntry] = []

        # ---- Category memory -------------------------------------------------
        if transaction.category_id:
            for signal_type, raw in signal_candidates:
                entry = self.remember(
                    user=user,
                    signal_type=signal_type,
                    signal_key=raw,
                    raw_signal=raw,
                    entity_type="category",
                    entity_value=transaction.category.name if transaction.category else "",
                    linked_category=transaction.category,
                    transaction_type=transaction.transaction_type,
                    confidence=95,
                    metadata={
                        "payment_method": transaction.payment_method,
                        "last_amount": float(transaction.amount or 0),
                    },
                )
                if entry:
                    created.append(entry)

        # ---- Goal memory -----------------------------------------------------
        if transaction.goal_id:
            for signal_type, raw in signal_candidates:
                entry = self.remember(
                    user=user,
                    signal_type=signal_type,
                    signal_key=raw,
                    raw_signal=raw,
                    entity_type="goal",
                    entity_value=transaction.goal.title if transaction.goal else "",
                    linked_goal=transaction.goal,
                    confidence=95,
                )
                if entry:
                    created.append(entry)

            # Also learn the goal's title tokens as ``account_hint`` so a
            # transfer titled "To Bike Savings" is recognised even if the
            # merchant field is empty.
            if transaction.goal and transaction.goal.title:
                self.remember(
                    user=user,
                    signal_type="account_hint",
                    signal_key=transaction.goal.title,
                    raw_signal=transaction.goal.title,
                    entity_type="goal",
                    entity_value=transaction.goal.title,
                    linked_goal=transaction.goal,
                    confidence=90,
                )

        # ---- Merchant alias memory ------------------------------------------
        if transaction.merchant:
            canonical = transaction.merchant.strip()
            for signal_type, raw in signal_candidates:
                if not raw or normalise_signal(raw) == normalise_signal(canonical):
                    continue
                entry = self.remember(
                    user=user,
                    signal_type=signal_type,
                    signal_key=raw,
                    raw_signal=raw,
                    entity_type="merchant_alias",
                    entity_value=canonical,
                    confidence=90,
                )
                if entry:
                    created.append(entry)
            # Track the alias
            MerchantAlias.objects.update_or_create(
                user=user,
                alias=normalise_signal(transaction.title or transaction.merchant),
                defaults={
                    "canonical_name": canonical,
                    "is_active": True,
                },
            )

        # ---- Salary source (income transactions) ----------------------------
        if transaction.transaction_type == "income" and transaction.category and \
                transaction.category.name.lower() in {"salary", "payroll"}:
            for signal_type, raw in signal_candidates:
                entry = self.remember(
                    user=user,
                    signal_type=signal_type,
                    signal_key=raw,
                    raw_signal=raw,
                    entity_type="salary_source",
                    entity_value=transaction.merchant or transaction.title,
                    transaction_type="income",
                    confidence=95,
                    metadata={"last_amount": float(transaction.amount or 0)},
                )
                if entry:
                    created.append(entry)

        return created

    # ---- READ PATH -------------------------------------------------------

    def match(self, user, description: str, entity_types: Iterable[str] | None = None) -> list[MemoryEntry]:
        """Return all memory entries whose signal_key is present in ``description``.

        The lookup is O(1) for exact-key hits and O(N) for the longest-prefix
        fallback on a very small subset of the user's memories.
        """
        if not user or not user.is_authenticated:
            return []
        key = normalise_signal(description)
        if not key:
            return []

        qs = MemoryEntry.objects.filter(user=user, is_active=True)
        if entity_types:
            qs = qs.filter(entity_type__in=list(entity_types))

        # 1) Exact key match — most confident.
        exact = list(qs.filter(signal_key=key))
        if exact:
            return exact

        # 2) Substring / token match. Restrict to the user's memories only.
        candidates = list(qs.only("id", "signal_key", "entity_type", "entity_value",
                                    "linked_category_id", "linked_goal_id",
                                    "linked_holding_id", "subcategory",
                                    "transaction_type", "confidence"))
        hits: list[MemoryEntry] = []
        tokens = set(key.split())
        for entry in candidates:
            skey = entry.signal_key
            if not skey:
                continue
            if skey in key or key in skey:
                hits.append(entry)
                continue
            # Token overlap: memory key entirely composed of tokens in the query.
            if set(skey.split()).issubset(tokens):
                hits.append(entry)

        # 3) Optional fuzzy match using RapidFuzz for near-misses.
        if not hits and len(candidates) < 500:
            try:
                from rapidfuzz import process, fuzz
                choices = {c.id: c.signal_key for c in candidates if c.signal_key}
                if choices:
                    result = process.extractOne(key, choices, scorer=fuzz.token_set_ratio)
                    if result and result[1] >= 88:
                        matched_id = result[2]
                        hits = [c for c in candidates if c.id == matched_id]
            except Exception:  # pragma: no cover
                logger.debug("RapidFuzz unavailable, skipping fuzzy match")

        return hits

    def classify(self, user, description: str, amount=None, fallback=True) -> ClassificationResult:
        """High-level entry point used by importers and manual entry.

        Returns a :class:`ClassificationResult` with the best-guess merchant /
        category / transaction-type derived from *this user's* memory.  If
        memory has nothing to say and ``fallback`` is True (default), we
        consult the global static merchant / pattern database as a floor.
        """
        result = ClassificationResult(source="unknown", confidence=0)

        matches = self.match(user, description)
        if matches:
            # Now organise: prefer category, alias, goal, subcategory in that order.
            by_type: dict[str, MemoryEntry] = {}
            for m in matches:
                by_type.setdefault(m.entity_type, m)

            alias = by_type.get("merchant_alias")
            if alias:
                result.merchant = alias.entity_value or alias.signal_key
                result.confidence = max(result.confidence, alias.confidence)
                result.entity_hits["merchant_alias"] = alias.entity_value

            category_hit = by_type.get("category")
            if category_hit:
                if category_hit.linked_category_id:
                    result.linked_category_id = category_hit.linked_category_id
                    result.category = category_hit.entity_value or (
                        category_hit.linked_category.name if category_hit.linked_category else ""
                    )
                else:
                    result.category = category_hit.entity_value
                result.transaction_type = category_hit.transaction_type or result.transaction_type
                result.subcategory = category_hit.subcategory or result.subcategory
                result.confidence = max(result.confidence, category_hit.confidence)
                result.entity_hits["category"] = result.category

            goal_hit = by_type.get("goal")
            if goal_hit and goal_hit.linked_goal_id:
                result.linked_goal_id = goal_hit.linked_goal_id
                result.entity_hits["goal"] = goal_hit.entity_value
                result.confidence = max(result.confidence, goal_hit.confidence)

            for extra in ("investment_platform", "salary_source", "subscription",
                          "loan", "emi", "utility", "insurance", "friend",
                          "family", "business", "transfer"):
                if extra in by_type:
                    result.entity_hits[extra] = by_type[extra].entity_value

            # Bump hit counters (best-effort, non-atomic).
            memory_ids = [m.id for m in matches]
            result.memory_ids = memory_ids
            MemoryEntry.objects.filter(id__in=memory_ids).update(
                hit_count=models_F("hit_count") + 1,
                last_matched_at=timezone.now(),
            )
            result.source = "memory"

            # If everything we needed came from memory, return early.
            if result.category or result.merchant or result.linked_goal_id:
                return result

        if fallback:
            # Consult the static merchant / pattern database. Import lazily.
            from transactions.importers.categorizer import TransactionCategorizer
            static = TransactionCategorizer.categorize(description)
            if static and static.get("confidence", 0) > result.confidence:
                result.merchant = result.merchant or static.get("merchant", "")
                result.category = result.category or static.get("category", "")
                result.confidence = max(result.confidence, int(static.get("confidence") or 0))
                result.source = "static"

        return result

    # ---- REVIEW QUEUE ----------------------------------------------------

    def enqueue_review(
        self,
        *,
        user,
        original_description: str,
        amount=0,
        transaction_type: str = "",
        transaction_date=None,
        source: str = "manual",
        merchant_guess: str = "",
        suggested_category: str = "",
        suggested_entity_type: str = "",
        confidence: int = 0,
        transaction=None,
        metadata: dict | None = None,
    ) -> ReviewQueueItem | None:
        """Store an unknown/low-confidence transaction for later review."""
        if not user or not user.is_authenticated or not original_description:
            return None
        return ReviewQueueItem.objects.create(
            user=user,
            original_description=(original_description or "")[:500],
            merchant_guess=(merchant_guess or "")[:255],
            suggested_category=(suggested_category or "")[:100],
            suggested_entity_type=suggested_entity_type or "",
            amount=amount or 0,
            transaction_type=transaction_type or "",
            transaction_date=transaction_date,
            confidence=max(0, min(100, int(confidence or 0))),
            source=source or "manual",
            transaction=transaction,
            metadata=metadata or {},
        )

    @db_transaction.atomic
    def resolve_review(
        self,
        *,
        user,
        review_id: int,
        category=None,
        goal=None,
        entity_type: str = "category",
        entity_value: str = "",
        signal_type: str = "merchant",
    ) -> MemoryEntry | None:
        """Move a review item into memory and mark the item resolved.

        If a linked :class:`Transaction` exists we also apply the correction
        to it directly so the dashboard reflects the fix immediately.
        """
        item = ReviewQueueItem.objects.select_for_update().get(id=review_id, user=user)

        signal_source = item.merchant_guess or item.original_description
        primary_entry = self.remember(
            user=user,
            signal_type=signal_type,
            signal_key=signal_source,
            raw_signal=item.original_description,
            entity_type=entity_type,
            entity_value=entity_value or (category.name if category else "") or (goal.title if goal else ""),
            linked_category=category,
            linked_goal=goal,
            transaction_type=item.transaction_type or "",
            confidence=95,
            metadata={"resolved_from_review": item.id},
        )

        # Whenever a category was chosen we ALSO write a canonical
        # ``category`` memory entry so future classify() calls resolve it
        # even if the user picked a different entity_type like ``subscription``.
        if category and entity_type != "category":
            self.remember(
                user=user,
                signal_type=signal_type,
                signal_key=signal_source,
                raw_signal=item.original_description,
                entity_type="category",
                entity_value=category.name,
                linked_category=category,
                transaction_type=item.transaction_type or "",
                confidence=95,
                metadata={"resolved_from_review": item.id},
            )

        # Similarly, a goal choice implies a ``goal`` memory entry.
        if goal and entity_type != "goal":
            self.remember(
                user=user,
                signal_type=signal_type,
                signal_key=signal_source,
                raw_signal=item.original_description,
                entity_type="goal",
                entity_value=goal.title,
                linked_goal=goal,
                confidence=95,
                metadata={"resolved_from_review": item.id},
            )

        # If a transaction row exists, update it too.
        if item.transaction_id:
            tx = item.transaction
            if category:
                tx.category = category
            if goal:
                tx.goal = goal
            if entity_value and not tx.merchant:
                tx.merchant = entity_value[:200]
            tx.save()

        item.status = "reviewed"
        item.reviewed_at = timezone.now()
        item.save(update_fields=["status", "reviewed_at"])
        return primary_entry

    # ---- ADMIN / DASHBOARD HELPERS ---------------------------------------

    def stats_for_user(self, user) -> dict:
        """Return summary counts used by the memory dashboard."""

        from .recurring_detector import RecurringDetector

        entries = MemoryEntry.objects.filter(
            user=user,
            is_active=True
        )

        pending = ReviewQueueItem.objects.filter(
            user=user,
            status="pending"
        ).count()

        aliases = MerchantAlias.objects.filter(
            user=user,
            is_active=True
        ).count()

        recurring = RecurringDetector.count(user)

        total_hits = sum(entries.values_list("hit_count", flat=True))

        # Unique learned entities
        unique_goals = (
            entries.filter(linked_goal__isnull=False)
            .values("linked_goal")
            .distinct()
            .count()
        )

        unique_categories = (
            entries.filter(linked_category__isnull=False)
            .values("linked_category")
            .distinct()
            .count()
        )

        unique_holdings = (
            entries.filter(linked_holding__isnull=False)
            .values("linked_holding")
            .distinct()
            .count()
        )

        total_memories = (
            unique_goals +
            unique_categories +
            unique_holdings +
            aliases
        )

        return {
            "total_memories": total_memories,
            "aliases": aliases,
            "recurring": recurring,
            "pending_reviews": pending,
            "total_hits": total_hits,

            # New stats
            "goal_count": unique_goals,
            "category_count": unique_categories,
            "holding_count": unique_holdings,
        }

    def summary_context(self, user) -> str:
        """A short, LLM-friendly description of what the memory knows.

        Used by the AI coach to answer questions like "what recurring
        subscriptions do I have?" without doing extra SQL.
        """
        from .recurring_detector import RecurringDetector
        entries = MemoryEntry.objects.filter(user=user, is_active=True)
        salaries = entries.filter(entity_type="salary_source").values_list("entity_value", flat=True)[:3]
        platforms = entries.filter(entity_type="investment_platform").values_list("entity_value", flat=True)[:5]
        recurring = RecurringDetector.top(user, limit=6)
        lines = []
        if salaries:
            lines.append("Known salary source(s): " + ", ".join(filter(None, salaries)))
        if platforms:
            lines.append("Known investment platform(s): " + ", ".join(filter(None, platforms)))
        if recurring:
            rlines = [f"  • {r.label} ({r.frequency}, avg ₹{r.avg_amount:.0f})" for r in recurring]
            lines.append("Recurring patterns:\n" + "\n".join(rlines))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fix for the deferred F() import (avoids naming collision at file scope)
# ---------------------------------------------------------------------------

def models_F(field_name: str):  # pragma: no cover — tiny shim
    from django.db.models import F
    return F(field_name)


# Module-level singleton — preferred entry point.
memory_service = MemoryService()

__all__ = [
    "MemoryService",
    "memory_service",
    "ClassificationResult",
    "normalise_signal",
]


@transaction.atomic
def remember_transactions(self, user, transactions):
    """
    Learn from a batch of imported transactions.

    Used by:
        - BankHub
        - PDF Import
        - CSV Import
        - Excel Import
        - Gmail Sync

    The signal ignores imported transactions, so all importers
    call this once after the import completes.
    """

    learned = 0

    # Skip duplicate objects in the same batch
    processed = set()

    for txn in transactions:

        if txn.pk in processed:
            continue

        processed.add(txn.pk)

        try:

            self.remember_correction(txn)

            learned += 1

        except Exception as e:

            print(
                f"[FinancialMemory] Failed on "
                f"Transaction {txn.pk}: {e}"
            )

    print(
        f"[FinancialMemory] Learned "
        f"{learned} imported transactions."
    )

    return learned
