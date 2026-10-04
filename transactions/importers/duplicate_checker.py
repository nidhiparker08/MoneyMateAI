from decimal import Decimal

from transactions.models import Transaction


class DuplicateChecker:
    """
    Checks whether an imported transaction already
    exists for the current user.
    """

    @staticmethod
    def is_duplicate(user, transaction):

        amount = Decimal(str(transaction["amount"]))

        qs = Transaction.objects.filter(

            user=user,

            amount=amount,

            transaction_date=transaction["date"],

            transaction_type=transaction["type"]

        )

        merchant = transaction.get("merchant", "").strip()

        if merchant:

            qs = qs.filter(

                merchant__iexact=merchant

            )

        return qs.exists()

    @staticmethod
    def mark_duplicates(user, transactions):

        for tx in transactions:

            tx["is_duplicate"] = DuplicateChecker.is_duplicate(

                user,

                tx

            )

        return transactions