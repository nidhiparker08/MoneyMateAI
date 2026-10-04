"""
Transaction Intelligence Layer
==============================

Enriches a raw transaction *before* it is saved / classified.
Reuses the existing "Financial Memory" primitives (MerchantCleaner,
TransactionCategorizer, MERCHANT_CATEGORIES, TRANSACTION_PATTERNS)
and the user's own transaction history — nothing here duplicates
that logic.

Pipeline (strict priority):
    1. Financial Memory        -> user's own past classifications
    2. Existing rules          -> transactions.importers.pattern_database
    3. Regex                   -> rules.type_patterns.TYPE_RULES
    4. Merchant dictionaries   -> transactions.importers.merchant_database
    5. Pattern matching        -> TransactionCategorizer (fuzzy/keyword)

Public API
----------
    TransactionIntelligence.analyze(
        description: str,
        *,
        amount: Decimal | float | None = None,
        direction: "credit" | "debit" | None = None,
        user=None,
        payment_method: str = "",
        goal=None,
    ) -> dict

The returned dict is guaranteed to have every key that the existing
`Transaction` model / `TransactionService.create_transaction()` and
`ImportService.import_transactions()` know how to consume, plus the
new enrichment fields (transaction_type_detail, subcategory, receiver,
confidence_score, intelligence_source, trace).
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Optional

from .importers.categorizer import TransactionCategorizer
from .importers.merchant_cleaner import MerchantCleaner
from .importers.merchant_database import MERCHANT_CATEGORIES
from .importers.pattern_database import TRANSACTION_PATTERNS
from .rules.receiver_patterns import (
    extract_receiver,
    looks_like_business,
    looks_like_self,
)
from .rules.type_patterns import (
    PAYMENT_METHOD_RULES,
    SUBCATEGORY_MAP,
    TYPE_RULES,
    T_BUSINESS_TRANSFER,
    T_EXPENSE,
    T_FRIEND_TRANSFER,
    T_GOAL_CONTRIB,
    T_INCOME,
    T_INTERNAL_TRANSFER,
    T_INVESTMENT,
    T_SALARY,
)


# --------------------------------------------------------------------
# The 17 detailed transaction types (locked contract)
# --------------------------------------------------------------------

DETAILED_TYPES = {
    "income", "expense",
    "investment", "goal_contribution", "salary", "insurance",
    "loan_emi", "subscription", "utility_bill", "cashback", "refund",
    "interest", "dividend", "tax",
    "internal_transfer", "friend_transfer", "business_transfer",
}


# Types that *always* imply a credit (income-like)
_CREDIT_TYPES = {"salary", "interest", "dividend", "cashback", "refund", "income"}

# Types that *always* imply a debit (expense-like)
_DEBIT_TYPES = {
    "investment", "goal_contribution", "insurance", "loan_emi",
    "subscription", "utility_bill", "tax", "expense",
}


# Words that should NOT drive a memory-match on their own — they are
# too common to carry classification signal.
_MEMORY_STOPWORDS = {
    "bank", "banking", "credit", "debit", "payment", "transfer",
    "txn", "txn.", "ref", "reference", "acct", "account",
    "hdfc", "sbi", "icici", "axis", "kotak", "yesbank", "pnb",
    "boi", "canara", "indus", "indusind", "idfc",
    "loan", "emi", "salary", "cheque", "amount", "paid",
    "cr", "dr", "in", "out", "to", "from", "self", "own",
    "india", "pvt", "ltd", "limited", "private",
    "upi", "imps", "neft", "rtgs", "pos", "atm",
    "store", "shop", "mart", "market",
}


class TransactionIntelligence:
    """
    A single, side-effect-free façade. Instantiate not required —
    all methods are classmethods so it composes cleanly with the
    existing services and importers.
    """

    # ================================================================
    # PUBLIC ENTRYPOINT
    # ================================================================

    @classmethod
    def analyze(
        cls,
        description: str,
        *,
        amount: Optional[Decimal | float] = None,
        direction: Optional[str] = None,
        user=None,
        payment_method: str = "",
        goal=None,
    ) -> dict:
        """
        Run the full intelligence pipeline.

        `direction` is "credit" (money in) or "debit" (money out).
        If None, we infer from other signals but fall back to "debit".

        Returns a dict — see module docstring.
        """

        raw = (description or "").strip()
        cleaned = MerchantCleaner.clean(raw)

        # Base skeleton (blanks — the pipeline fills them).
        result = {
            "merchant": "",
            "receiver": "",
            "transaction_type": "",           # legacy: income/expense (Transaction.transaction_type)
            "transaction_type_detail": "",    # fine-grained (17 types)
            "category": "",
            "subcategory": "",
            "payment_method": payment_method or "",
            "confidence_score": 0,
            "intelligence_source": "default",
            "trace": [],
        }

        # ---------------- 1. Financial Memory (strict override) ----------------
        memory_hit = None
        if user is not None:
            memory_hit = cls._from_memory(user=user, cleaned=cleaned, raw=raw)
            if memory_hit:
                cls._merge(result, memory_hit, source="memory", authoritative=True)

        # When memory has spoken, downstream layers can ONLY fill blanks
        # (they cannot override category/type/type_detail/source).
        blanks_only = memory_hit is not None

        # ---------------- 2. Existing rules (pattern DB) → CATEGORY ----------------
        hit = cls._from_existing_rules(cleaned)
        if hit:
            cls._merge(result, hit, source="rules", authoritative=not blanks_only)

        # ---------------- 3. Regex TYPE_RULES → DETAILED TYPE ----------------
        hit = cls._from_regex(raw, cleaned)
        if hit:
            cls._merge(result, hit, source="regex", authoritative=not blanks_only)

        # ---------------- 4. Merchant dictionaries → CATEGORY + MERCHANT ----------------
        hit = cls._from_merchant_dictionaries(cleaned)
        if hit:
            cls._merge(result, hit, source="dictionary", authoritative=not blanks_only)

        # ---------------- 5. Fuzzy / pattern matching ----------------
        if result["confidence_score"] < 60:
            hit = cls._from_pattern_matching(raw)
            if hit:
                cls._merge(result, hit, source="pattern", authoritative=not blanks_only)

        # ---------------- Enrichment: receiver, payment method ----------------
        if not result["receiver"]:
            result["receiver"] = extract_receiver(raw)

        if not result["payment_method"]:
            result["payment_method"] = cls._detect_payment_method(raw)

        # ---------------- Direction reconciliation ----------------
        direction = direction or cls._infer_direction(result, amount)
        cls._reconcile_types(result, direction, goal=goal)

        # ---------------- Subcategory overlay ----------------
        if not result["subcategory"]:
            result["subcategory"] = cls._subcategory_for(cleaned)

        # ---------------- Final safety ----------------
        if not result["transaction_type"]:
            result["transaction_type"] = "expense" if direction == "debit" else "income"
        if not result["category"]:
            result["category"] = "Other"
        if not result["merchant"]:
            result["merchant"] = cleaned or raw[:120]
        if result["transaction_type_detail"] not in DETAILED_TYPES:
            result["transaction_type_detail"] = result["transaction_type"]

        return result

    # ================================================================
    # STEP 1 : FINANCIAL MEMORY
    # ================================================================

    @classmethod
    def _from_memory(cls, *, user, cleaned: str, raw: str) -> Optional[dict]:
        """
        Consult the user's own transaction history.

        Strategy (strict — false positives here corrupt every future
        classification for this user):
          * Compute the *cleaned* merchant/title of every candidate row.
          * A candidate matches iff:
              - the current cleaned text is contained in the candidate's
                cleaned text, OR
              - the candidate's cleaned text is contained in the current one, OR
              - Jaccard(word_set) >= 0.6 with at least one "meaningful"
                token (>= 4 chars, not a stop-word).
          * We vote on the (category, transaction_type_detail) tuple.
          * Confidence scales with the number of confirming past entries.

        This deliberately IGNORES 1-word overlaps on generic terms
        like "hdfc", "loan", "bank", "credit" which would otherwise
        cause spurious matches.
        """
        target = (cleaned or "").strip().lower()
        if not target:
            return None

        target_tokens = {t for t in target.split() if len(t) >= 3}
        if not target_tokens:
            return None

        meaningful_target = {
            t for t in target_tokens
            if len(t) >= 4 and t not in _MEMORY_STOPWORDS
        }
        if not meaningful_target:
            return None

        from .models import Transaction

        rows = (
            Transaction.objects
            .filter(user=user)
            .exclude(merchant="", title="")
            .only(
                "id", "title", "merchant", "category_id",
                "transaction_type", "transaction_type_detail",
                "subcategory", "payment_method",
            )
            .order_by("-id")[:500]
        )

        matches = []
        for r in rows:
            row_text = ((r.merchant or "") + " " + (r.title or "")).lower()
            row_clean = MerchantCleaner.clean(row_text)
            if not row_clean:
                continue
            # Cheap substring test first.
            if target and (target in row_clean or row_clean in target):
                matches.append(r)
                continue
            # Jaccard fallback for near-duplicates.
            row_tokens = {t for t in row_clean.split() if len(t) >= 3}
            if not row_tokens:
                continue
            common = target_tokens & row_tokens
            meaningful_common = {
                t for t in common
                if len(t) >= 4 and t not in _MEMORY_STOPWORDS
            }
            if not meaningful_common:
                continue
            union = target_tokens | row_tokens
            jaccard = len(common) / len(union) if union else 0
            if jaccard >= 0.6:
                matches.append(r)

        if not matches:
            return None

        # Vote on the classification the user has confirmed most.
        cat_ids       = Counter(m.category_id for m in matches if m.category_id)
        type_details  = Counter(
            m.transaction_type_detail for m in matches if m.transaction_type_detail
        )
        base_types    = Counter(m.transaction_type for m in matches)
        subcats       = Counter(m.subcategory for m in matches if m.subcategory)
        pmethods      = Counter(m.payment_method for m in matches if m.payment_method)

        top_category = None
        if cat_ids:
            top_cat_id = cat_ids.most_common(1)[0][0]
            from .models import TransactionCategory
            top_category = TransactionCategory.objects.filter(id=top_cat_id).first()

        top_type_detail = type_details.most_common(1)[0][0] if type_details else ""
        top_base_type   = base_types.most_common(1)[0][0] if base_types else ""
        top_subcat      = subcats.most_common(1)[0][0] if subcats else ""
        top_pmethod     = pmethods.most_common(1)[0][0] if pmethods else ""

        # Confidence: 85 base + 2 per confirming entry, capped at 99.
        # Memory ALWAYS ranks above rules/regex/dictionary so it stays
        # authoritative once seen (see analyze()'s blanks_only flag).
        confidence = min(99, 85 + 2 * min(len(matches), 7))

        return {
            "merchant": matches[0].merchant or cleaned,
            "category": top_category.name if top_category else "",
            "transaction_type": top_base_type or "",
            "transaction_type_detail": top_type_detail,
            "subcategory": top_subcat,
            "payment_method": top_pmethod,
            "confidence_score": confidence,
            "intelligence_source": "memory",
        }

    # ================================================================
    # STEP 2 : EXISTING RULES (pattern_database.py)
    # ================================================================

    @classmethod
    def _from_existing_rules(cls, cleaned: str) -> Optional[dict]:
        """
        Consult the *existing* pattern database for the CATEGORY only.

        We deliberately do NOT set transaction_type_detail here — the
        pattern_database maps things like "dividend" → "Investment"
        which is fine as a category but too coarse as a detailed type.
        The dedicated regex layer (step 3) owns type_detail.
        """
        if not cleaned:
            return None
        # Sort longest-first so "salary credit" wins over "salary".
        for pattern in sorted(TRANSACTION_PATTERNS.keys(), key=len, reverse=True):
            if pattern in cleaned:
                return {
                    "category": TRANSACTION_PATTERNS[pattern],
                    "confidence_score": 92,
                    "intelligence_source": "rules",
                }
        return None

    # ================================================================
    # STEP 3 : REGEX (rules.type_patterns.TYPE_RULES)
    # ================================================================

    @classmethod
    def _from_regex(cls, raw: str, cleaned: str) -> Optional[dict]:
        text = f"{raw} {cleaned}"
        for regex, detail, subcat, conf in TYPE_RULES:
            if regex.search(text):
                return {
                    "transaction_type_detail": detail,
                    "subcategory": subcat,
                    "confidence_score": conf,
                    "intelligence_source": "regex",
                }
        return None

    # ================================================================
    # STEP 4 : MERCHANT DICTIONARIES (merchant_database.py)
    # ================================================================

    @classmethod
    def _from_merchant_dictionaries(cls, cleaned: str) -> Optional[dict]:
        if not cleaned:
            return None
        for merchant in sorted(MERCHANT_CATEGORIES.keys(), key=len, reverse=True):
            if merchant in cleaned:
                return {
                    "merchant": merchant,
                    "category": MERCHANT_CATEGORIES[merchant],
                    "confidence_score": 88,
                    "intelligence_source": "dictionary",
                }
        return None

    # ================================================================
    # STEP 5 : Fuzzy pattern matching via existing TransactionCategorizer
    # ================================================================

    @classmethod
    def _from_pattern_matching(cls, raw: str) -> Optional[dict]:
        try:
            hit = TransactionCategorizer.categorize(raw) or {}
        except Exception:
            hit = {}
        if not hit or hit.get("category") == TransactionCategorizer.DEFAULT_CATEGORY:
            return None
        return {
            "merchant": hit.get("merchant") or "",
            "category": hit.get("category") or "",
            "confidence_score": int(hit.get("confidence", 40) or 40),
            "intelligence_source": "pattern",
        }

    # ================================================================
    # Helpers
    # ================================================================

    @staticmethod
    def _merge(result: dict, hit: dict, *, source: str, authoritative: bool = True) -> None:
        """
        Overlay `hit` onto `result`.

        - Blank fields on `result` are always filled from `hit`.
        - Non-blank fields on `result` are overwritten only when
          `authoritative=True` AND `hit`'s confidence is higher.
        - `intelligence_source` updates iff the current layer becomes
          the highest-confidence authoritative decider.
        """
        new_conf = int(hit.get("confidence_score", 0) or 0)

        for k, v in hit.items():
            if k in {"trace", "confidence_score", "intelligence_source"}:
                continue
            if v in (None, "", 0):
                continue
            existing = result.get(k)
            is_blank = existing in (None, "", 0)
            if is_blank:
                result[k] = v
            elif authoritative and new_conf > result["confidence_score"]:
                result[k] = v

        if new_conf > result["confidence_score"] and authoritative:
            result["confidence_score"] = new_conf
            result["intelligence_source"] = source
        elif result["confidence_score"] == 0 and new_conf > 0:
            # blank-fill scenario — record source but don't inflate confidence
            result["confidence_score"] = new_conf
            result["intelligence_source"] = source

        result["trace"].append(
            (source, {k: v for k, v in hit.items() if k != "trace"})
        )

    @staticmethod
    def _detect_payment_method(raw: str) -> str:
        for regex, method in PAYMENT_METHOD_RULES:
            if regex.search(raw or ""):
                return method
        return ""

    @staticmethod
    def _subcategory_for(cleaned: str) -> str:
        if not cleaned:
            return ""
        for key in sorted(SUBCATEGORY_MAP.keys(), key=len, reverse=True):
            if key in cleaned:
                return SUBCATEGORY_MAP[key]
        return ""

    @staticmethod
    def _infer_direction(result: dict, amount) -> str:
        """Best-effort credit/debit guess when caller didn't supply it."""
        detail = result.get("transaction_type_detail") or ""
        if detail in _CREDIT_TYPES:
            return "credit"
        if detail in _DEBIT_TYPES:
            return "debit"
        base = (result.get("transaction_type") or "").lower()
        if base == "income":
            return "credit"
        if base == "expense":
            return "debit"
        # Default: assume outgoing.
        return "debit"

    @staticmethod
    def _reconcile_types(result: dict, direction: str, *, goal=None) -> None:
        """
        Given the direction (credit/debit) and prior signals, fill in
        `transaction_type` (income/expense) and finalise
        `transaction_type_detail` for the transfer sub-classes.
        """

        detail = result.get("transaction_type_detail") or ""
        base   = result.get("transaction_type") or ""

        # (a) Explicit goal contribution wins.
        if goal is not None:
            result["transaction_type_detail"] = T_GOAL_CONTRIB
            result["transaction_type"] = "expense"
            result["subcategory"] = result["subcategory"] or "Goal Contribution"
            result["intelligence_source"] = result["intelligence_source"] or "rules"
            return

        # (b) If detail is a "transfer" placeholder, classify further.
        if detail in {"transfer", ""} and (
            "imps" in (result["merchant"] or "").lower()
            or "neft" in (result["merchant"] or "").lower()
        ):
            detail = ""  # fall through

        # (c) Refine generic "transfer" → internal / friend / business
        finalized_by_receiver = False
        if detail in {"transfer", ""}:
            recv = result.get("receiver") or ""
            if looks_like_self(result.get("merchant", ""), recv):
                detail = T_INTERNAL_TRANSFER
                finalized_by_receiver = True
            elif recv and looks_like_business(recv):
                detail = T_BUSINESS_TRANSFER
                finalized_by_receiver = True
            elif recv:
                detail = T_FRIEND_TRANSFER
                finalized_by_receiver = True

        # (d) If we still have no detail, fall back to income/expense by direction.
        if not detail:
            detail = T_INCOME if direction == "credit" else T_EXPENSE

        # (e) Ensure legacy `transaction_type` matches direction.
        if direction == "credit":
            base = "income"
        else:
            base = "expense"

        # (f) Some detail types imply the direction — override if inconsistent.
        if detail in _CREDIT_TYPES and base != "income":
            base = "income"
        if detail in _DEBIT_TYPES and base != "expense":
            base = "expense"

        result["transaction_type_detail"] = detail
        result["transaction_type"]        = base

        # (g) Bump confidence when the transfer subtype was derived from
        # the extracted receiver — this is a real signal, not a guess.
        if finalized_by_receiver and result["confidence_score"] < 70:
            result["confidence_score"] = 70
            if not result.get("intelligence_source") or result["intelligence_source"] == "default":
                result["intelligence_source"] = "regex"


# --------------------------------------------------------------------
# Convenience wrapper used by TransactionService.create_transaction()
# --------------------------------------------------------------------

def enrich_for_create(
    *,
    user,
    title: str,
    merchant: str = "",
    amount=None,
    transaction_type: str = "",
    payment_method: str = "",
    notes: str = "",
    goal=None,
) -> dict:
    """
    Called from TransactionService.create_transaction().
    Runs the intelligence pipeline and returns the enrichment dict
    WITHOUT overriding any explicit field the caller already provided.
    """
    description = " ".join(x for x in [title, merchant, notes] if x)
    direction = "credit" if transaction_type == "income" else (
        "debit" if transaction_type == "expense" else None
    )

    analysis = TransactionIntelligence.analyze(
        description,
        amount=amount,
        direction=direction,
        user=user,
        payment_method=payment_method,
        goal=goal,
    )

    # Never override explicit user input.
    if merchant:
        analysis["merchant"] = merchant
    if transaction_type:
        analysis["transaction_type"] = transaction_type
    if payment_method:
        analysis["payment_method"] = payment_method

    return analysis
