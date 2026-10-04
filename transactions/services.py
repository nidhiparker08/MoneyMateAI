from django.db import transaction as db_transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.utils import timezone
from .intelligence import TransactionIntelligence, enrich_for_create
from .models import TransactionCategory
from .models import Transaction


class TransactionService:

    # ============================================
    # CREATE
    # ============================================

    @staticmethod
    @db_transaction.atomic
    def create_transaction(
            *,
            user,
            title,
            amount,
            transaction_type,
            category,
            payment_method,
            transaction_date,
            transaction_time=None,
            merchant="",
            notes="",
            import_source="manual",
            goal=None,
        ):

        # ------------------------------------------------------------
        # Future-date guard: a transaction cannot be recorded for
        # upcoming days/hours.
        # ------------------------------------------------------------
        today = timezone.localdate()
        if transaction_date > today:
            raise ValidationError(
                "Transaction date cannot be in the future."
            )
        if (
            transaction_date == today
            and transaction_time is not None
            and transaction_time > timezone.localtime().time()
        ):
            raise ValidationError(
                "Transaction time cannot be in the future."
            )

        # ------------------------------------------------------------
        # Transaction Intelligence Layer
        # Runs BEFORE persisting; never overrides fields the caller
        # explicitly provided. Populates the enrichment columns.
        # ------------------------------------------------------------
        enrichment = enrich_for_create(
            user=user,
            title=title,
            merchant=merchant,
            amount=amount,
            transaction_type=transaction_type,
            payment_method=payment_method,
            notes=notes,
            goal=goal,
        )

        final_merchant       = merchant.strip() or enrichment.get("merchant", "")
        final_payment_method = payment_method or enrichment.get("payment_method", "upi")

        return Transaction.objects.create(

            user=user,

            title=title.strip(),

            merchant=final_merchant,

            amount=amount,

            transaction_type=transaction_type,

            category=category,

            goal=goal,

            payment_method=final_payment_method,

            transaction_date=transaction_date,

            transaction_time=transaction_time,

            notes=notes.strip(),

            import_source=import_source,

            # ---- Enrichment fields ----
            transaction_type_detail=enrichment.get("transaction_type_detail", "")[:32],
            subcategory=enrichment.get("subcategory", "")[:64],
            receiver=enrichment.get("receiver", "")[:120],
            confidence_score=int(enrichment.get("confidence_score", 0) or 0),
            intelligence_source=("manual" if import_source == "manual" and enrichment.get("confidence_score", 0) < 50
                                 else enrichment.get("intelligence_source", "default"))[:24],

        )

    # ============================================
    # GET
    # ============================================

    @staticmethod
    def get_transaction(user, transaction_id):

        return get_object_or_404(

            Transaction,

            id=transaction_id,

            user=user,

        )

    # ============================================
    # UPDATE
    # ============================================

    @staticmethod
    @db_transaction.atomic
    def update_transaction(
        user,
        transaction_id,
        **kwargs
    ):

        transaction = TransactionService.get_transaction(
            user,
            transaction_id,
        )

        for field, value in kwargs.items():
            setattr(transaction, field, value)

        transaction.save()

        return transaction

    # ============================================
    # DELETE
    # ============================================

    @staticmethod
    @db_transaction.atomic
    def delete_transaction(user, transaction_id):

        transaction = TransactionService.get_transaction(

            user,

            transaction_id,

        )

        transaction.delete()

        return True

    # ============================================
    # LIST
    # ============================================

    @staticmethod
    def get_recent_transactions(user, limit=5):

        return (

            Transaction.objects

            .filter(user=user)

            .select_related("category")

            .order_by("-transaction_date", "-created_at")[:limit]

        )

    @staticmethod
    def get_all_transactions(user):

        return (

            Transaction.objects

            .filter(user=user)

            .select_related("category")

            .order_by("-transaction_date", "-created_at")

        )

    # ============================================
    # GET JSON
    # ============================================

    @staticmethod
    def get_transaction_json(user, transaction_id):

        transaction = TransactionService.get_transaction(

            user,

            transaction_id,

        )

        return {

            "id": transaction.id,

            "title": transaction.title,

            "merchant": transaction.merchant,

            "amount": float(transaction.amount),

            "transaction_type": transaction.transaction_type,

            "category": transaction.category.id if transaction.category else "",

            "payment_method": transaction.payment_method,

            "transaction_date": transaction.transaction_date.strftime("%Y-%m-%d"),

            "transaction_time": (

                transaction.transaction_time.strftime("%H:%M")

                if transaction.transaction_time

                else ""

            ),

            "notes": transaction.notes,

        }

        # ============================================
    # SEARCH & FILTER
    # ============================================

    @staticmethod
    def search_transactions(
        user,
        query="",
        transaction_type="",
        category="",
        sort="-transaction_date",
    ):

        transactions = (

            Transaction.objects

            .filter(user=user)

            .select_related("category")

        )

        # Search

        if query:

            transactions = transactions.filter(

                Q(title__icontains=query)

                |

                Q(merchant__icontains=query)

                |

                Q(notes__icontains=query)

                |

                Q(category__name__icontains=query)

            )

        # Transaction Type

        if transaction_type:

            transactions = transactions.filter(

                transaction_type=transaction_type

            )

        # Category

        if category:

            transactions = transactions.filter(

                category_id=category

            )

        return transactions.order_by(

            sort,

            "-created_at",

        )

class ImportService:

    @staticmethod
    @db_transaction.atomic
    def import_transactions(user, transactions):

        imported = 0
        duplicates = 0
        failed = 0

        for tx in transactions:

            try:

                # Skip duplicates detected during preview
                if tx.get("is_duplicate", False):
                    duplicates += 1
                    continue

                # ------------------------------------------------
                # Run the Transaction Intelligence Layer for any
                # row that is missing category / type / merchant.
                # We use it ONLY to fill blanks — never to overwrite
                # explicit values from the parser.
                # ------------------------------------------------
                needs_intel = not tx.get("category") or not tx.get("type") or not tx.get("merchant")
                if needs_intel:
                    description = " ".join(
                        s for s in [tx.get("title", ""), tx.get("merchant", ""), tx.get("notes", "")]
                        if s
                    )
                    direction = None
                    if tx.get("type") == "income":
                        direction = "credit"
                    elif tx.get("type") == "expense":
                        direction = "debit"

                    intel = TransactionIntelligence.analyze(
                        description,
                        amount=tx.get("amount"),
                        direction=direction,
                        user=user,
                        payment_method=tx.get("payment_method", ""),
                    )
                    tx.setdefault("category", intel["category"])
                    tx["category"] = tx.get("category") or intel["category"] or "Other"
                    tx["type"] = tx.get("type") or intel["transaction_type"]
                    tx["merchant"] = tx.get("merchant") or intel["merchant"]
                    tx.setdefault("subcategory", intel["subcategory"])
                    tx.setdefault("receiver", intel["receiver"])
                    tx.setdefault("transaction_type_detail", intel["transaction_type_detail"])
                    tx.setdefault("confidence_score", intel["confidence_score"])
                    tx.setdefault("intelligence_source", intel["intelligence_source"])
                    tx.setdefault("payment_method",
                                  intel["payment_method"] or tx.get("payment_method", "other"))

                category = (

                    TransactionCategory.objects

                    .filter(

                        Q(user=user) | Q(is_default=True),

                        name__iexact=tx["category"]

                    )

                    .first()

                )

                TransactionService.create_transaction(

                    user=user,

                    title=tx["title"],

                    merchant=tx["merchant"],

                    amount=tx["amount"],

                    transaction_type=tx["type"],

                    category=category,

                    payment_method=tx.get(
                        "payment_method",
                        "other"
                    ),

                    transaction_date=tx["date"],

                    transaction_time=tx.get(
                        "transaction_time"
                    ),

                    notes=tx.get(
                        "notes",
                        ""
                    ),

                    import_source=tx.get(
                        "source",
                        "csv"
                    ),

                )

                imported += 1

            except Exception:

                failed += 1

        return {

            "imported": imported,

            "duplicates": duplicates,

            "failed": failed,

        }