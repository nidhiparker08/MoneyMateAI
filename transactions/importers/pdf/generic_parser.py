import io
import re

import pandas as pd
import pdfplumber

from ..normalizer import StatementNormalizer
from ..categorizer import TransactionCategorizer


class GenericPDFParser:

    REQUIRED_COLUMNS = [
        "date",
        "description",
    ]

    def __init__(self, pdf_bytes):

        self.pdf_bytes = pdf_bytes

    def parse(self):

        rows = self.extract_rows()

        if not rows:

            raise ValueError(
                "No transaction table found."
            )

        df = pd.DataFrame(rows)

        df = StatementNormalizer(df).normalize()

        self.validate(df)

        return self.build_transactions(df)

    def validate(self, df):

        for col in self.REQUIRED_COLUMNS:

            if col not in df.columns:

                raise ValueError(
                    f"{col} column not found."
                )

    def extract_rows(self):

        rows = []
        mapping = None

        with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:

            for page in pdf.pages:

                tables = page.extract_tables()

                if not tables:
                    continue

                for table in tables:

                    if len(table) < 2:
                        continue

                    # Detect header
                    first_row = [
                        str(c).replace("\n", " ").strip().lower() if c else ""
                        for c in table[0]
                    ]

                    if any("date" in col for col in first_row):

                        mapping = {}

                        for i, col in enumerate(first_row):

                            if "date" in col:
                                mapping["date"] = i

                            elif (
                                "description" in col
                                or "narration" in col
                                or "particular" in col
                                or "remarks" in col
                                or "details" in col
                            ):
                                mapping["description"] = i

                            elif (
                                "withdraw" in col
                                or "debit" in col
                                or col == "dr"
                            ):
                                mapping["debit"] = i

                            elif (
                                "deposit" in col
                                or "credit" in col
                                or col == "cr"
                            ):
                                mapping["credit"] = i

                            elif "balance" in col:
                                mapping["balance"] = i

                        data_rows = table[1:]

                    else:

                        if mapping is None:
                            continue

                        data_rows = table

                    if (
                        "date" not in mapping
                        or
                        "description" not in mapping
                    ):
                        continue

                    for row in data_rows:

                        if not row:
                            continue

                        try:

                            rows.append({

                                "date": row[mapping["date"]],

                                "description": row[mapping["description"]],

                                "debit": row[mapping["debit"]] if "debit" in mapping else "",

                                "credit": row[mapping["credit"]] if "credit" in mapping else "",

                                "balance": row[mapping["balance"]] if "balance" in mapping else "",

                            })

                        except (IndexError, KeyError):
                            continue

        return rows

    def build_transactions(self, df):

        transactions = []

        for _, row in df.iterrows():

            debit = row.get("debit")
            credit = row.get("credit")

            amount = None
            tx_type = None

            if pd.notna(debit) and debit > 0:

                amount = float(debit)
                tx_type = "expense"

            elif pd.notna(credit) and credit > 0:

                amount = float(credit)
                tx_type = "income"

            if amount is None:
                continue

            description = str(
                row.get(
                    "description",
                    ""
                )
            ).strip()

            cat = TransactionCategorizer.categorize(
                description
            )

            transactions.append({

                "title": description,

                "description": description,

                "merchant": cat["merchant"],

                "category": cat["category"],

                "amount": amount,

                "type": tx_type,

                "payment_method": "other",

                "transaction_time": None,

                "notes": "",

                "date":

                row["date"].strftime("%Y-%m-%d")

                if pd.notna(row["date"])

                else None,

                "balance":

                float(row["balance"])

                if (
                    "balance" in row
                    and
                    pd.notna(row["balance"])
                )

                else None,

                "confidence": cat["confidence"],

                "source": "pdf",

            })

        return transactions