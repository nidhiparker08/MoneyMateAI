from decimal import Decimal
from datetime import datetime

from django.db import transaction

from transactions.models import Transaction
from investments.models import Investment


class BankHubImporter:

    @staticmethod
    @transaction.atomic
    def import_data(user, bankhub_data):

        account = bankhub_data["account"]
        transactions = bankhub_data["transactions"]
        investments = bankhub_data["investments"]

        imported_transactions = 0
        imported_investments = 0

        # ---------------------------------------
        # Import Transactions
        # ---------------------------------------

        for txn in transactions:

            txn_datetime = datetime.strptime(
                f"{txn['date']} {txn['time']}",
                "%Y-%m-%d %H:%M:%S"
            )

            Transaction.objects.create(

                user=user,

                date=txn_datetime.date(),

                time=txn_datetime.time(),

                amount=Decimal(str(txn["amount"])),

                transaction_type=txn["type"],

                category=txn["category"],

                merchant=txn["merchant"],

                description=txn["description"],

                payment_method=txn["payment_method"],

                sender=txn["sender"],

                receiver=txn["receiver"],

                reference_number=txn["reference"],

                balance_after_transaction=Decimal(
                    str(txn["balance"])
                ),

                status=txn["status"],

                source="BANKHUB"

            )

            imported_transactions += 1

        # ---------------------------------------
        # Import Investments
        # ---------------------------------------

        for inv in investments:

            Investment.objects.create(

                user=user,

                investment_type=inv["investment_type"],

                broker=inv["broker"],

                instrument_name=inv["instrument_name"],

                symbol=inv["symbol"],

                quantity=Decimal(str(inv["quantity"])),

                average_price=Decimal(
                    str(inv["average_price"])
                ),

                invested_amount=Decimal(
                    str(inv["invested_amount"])
                ),

                current_value=Decimal(
                    str(inv["current_value"])
                ),

                current_price=Decimal(
                    str(inv["current_price"])
                ),

                purchase_date=datetime.strptime(
                    inv["purchase_date"],
                    "%Y-%m-%d"
                ).date()

            )

            imported_investments += 1

        return {

            "success": True,

            "bank": account["bank"],

            "account_number": account["account_number"],

            "transactions_imported": imported_transactions,

            "investments_imported": imported_investments

        }