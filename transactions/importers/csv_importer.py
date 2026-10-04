import pandas as pd

from .normalizer import StatementNormalizer
from .categorizer import TransactionCategorizer


class CSVImporter:
    """
    Reads CSV bank statements and converts them into
    MoneyMate's standard transaction format.
    """

    REQUIRED_COLUMNS = [
        "date",
        "description",
    ]

    def __init__(self, uploaded_file, user=None):
        self.uploaded_file = uploaded_file
        self.user = user

    def parse(self):

        try:
            df = pd.read_csv(
                self.uploaded_file,
                encoding="utf-8"
            )

        except UnicodeDecodeError:

            df = pd.read_csv(
                self.uploaded_file,
                encoding="latin-1"
            )

        df = StatementNormalizer(df).normalize()
        print(df.columns.tolist())
        print(df.head())

        self._validate(df)

        return self._build_transactions(df)

    def _validate(self, df):

        missing = []

        for column in self.REQUIRED_COLUMNS:

            if column not in df.columns:
                missing.append(column)

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(missing)}"
            )

    def _build_transactions(self, df):

        transactions = []

        for _, row in df.iterrows():

            debit = row.get("debit")
            credit = row.get("credit")

            amount = None
            transaction_type = None

            print(debit, type(debit))

            if pd.notna(debit) and debit > 0:
                amount = float(debit)
                transaction_type = "expense"

            elif pd.notna(credit) and credit > 0:
                amount = float(credit)
                transaction_type = "income"

            if amount is None:
                continue

            description = str(
                row.get("description", "")
            ).strip()

            categorization = TransactionCategorizer.categorize(
                description, user=self.user
            )

            transactions.append({

                "title": description,

                "description": description,

                "merchant": categorization["merchant"],

                "category": categorization["category"],

                "amount": amount,

                "type": transaction_type,

                "payment_method": "other",

                "transaction_time": None,

                "notes": "",

                "date": (
                    row.get("date").strftime("%Y-%m-%d")
                    if pd.notna(row.get("date"))
                    else None
                ),

                "balance": (
                    float(row["balance"])
                    if "balance" in row and pd.notna(row["balance"])
                    else None
                ),

                "confidence": categorization["confidence"],

                "source": "csv",

            })

        return transactions