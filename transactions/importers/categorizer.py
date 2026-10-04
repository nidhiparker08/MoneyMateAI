from .merchant_cleaner import MerchantCleaner
from .merchant_database import MERCHANT_CATEGORIES
from rapidfuzz import fuzz


class TransactionCategorizer:
    """
    Categorizes transactions using merchant keywords.

    Priority order:
      1. Per-user Financial Memory (learned from prior corrections)
      2. Global pattern database (SALARY, EMI, SIP, etc.)
      3. Global merchant database (Amazon, Zomato, etc.)
      4. Default "Others"

    ``user`` is optional; when provided we consult the Financial Memory
    Engine first so learned corrections always win.
    """

    DEFAULT_CATEGORY = "Others"

    @classmethod
    def categorize(cls, description, user=None):

        cleaned = MerchantCleaner.clean(description)

        if not cleaned:
            return {
                "merchant": "",
                "category": cls.DEFAULT_CATEGORY,
                "confidence": 0.0,
            }

        # --------------------------
        # 1) Financial Memory (per-user learned mappings)
        # --------------------------

        if user is not None and getattr(user, "is_authenticated", False):
            try:
                from financial_memory.services import memory_service
                result = memory_service.classify(user, description, fallback=False)
                if result.confidence >= 60 and (result.category or result.merchant):
                    return {
                        "merchant": result.merchant or "",
                        "category": result.category or cls.DEFAULT_CATEGORY,
                        "confidence": int(result.confidence),
                        "memory": True,
                        "linked_category_id": result.linked_category_id,
                        "linked_goal_id": result.linked_goal_id,
                        "entity_hits": result.entity_hits,
                    }
            except Exception:
                # Memory is best-effort; never block imports.
                pass

        # --------------------------
        # 2) Pattern Matching (Highest priority among static rules)
        # --------------------------

        from .pattern_database import TRANSACTION_PATTERNS

        patterns = sorted(
            TRANSACTION_PATTERNS.keys(),
            key=len,
            reverse=True,
        )

        for pattern in patterns:

            if pattern in cleaned:

                return {

                    "merchant": "",

                    "category": TRANSACTION_PATTERNS[pattern],

                    "confidence": 98,

                }

        # --------------------------
        # 3) Merchant Matching
        # --------------------------

        merchants = sorted(
            MERCHANT_CATEGORIES.keys(),
            key=len,
            reverse=True,
        )

        for merchant in merchants:

            if merchant in cleaned:

                return {

                    "merchant": merchant,

                    "category": MERCHANT_CATEGORIES[merchant],

                    "confidence": 99,

                }

        # --------------------------
        # 4) Default
        # --------------------------

        return {

            "merchant": cleaned,

            "category": cls.DEFAULT_CATEGORY,

            "confidence": 15,

        }

    @classmethod
    def _find_best_merchant(cls, cleaned):

        best_match = None
        best_score = 0

        for merchant in MERCHANT_CATEGORIES.keys():

            score = fuzz.partial_ratio(
                cleaned,
                merchant
            )
            if score > best_score:
                best_score = score
                best_match = merchant

        return best_match, best_score
