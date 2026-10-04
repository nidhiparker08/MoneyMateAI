from datetime import datetime
import pandas as pd


class StatementNormalizer:
    """
    Converts different bank statement formats into
    one standard dataframe.
    """

    COLUMN_ALIASES = {
        "date": [
            "date",
            "transaction date",
            "txn date",
            "value date",
            "posting date",
        ],

        "description": [
            "description",
            "details",
            "particulars",
            "remarks",
            "narration",
            "transaction details",
        ],

        "debit": [
            "debit",
            "debit (₹)",
            "debit amount",
            "withdrawal",
            "withdraw",
            "dr",
            "paid out",
        ],

        "credit": [
            "credit",
            "credit (₹)",
            "credit amount",
            "deposit",
            "cr",
            "paid in",
        ],

        "balance": [
            "balance",
            "balance (₹)",
            "closing balance",
            "running balance",
        ],
    }

    def __init__(self, dataframe: pd.DataFrame):
        self.df = dataframe.copy()

    def normalize(self):

        self._clean_columns()

        self._rename_columns()

        self._parse_dates()

        self._clean_amounts()

        return self.df

    def _clean_columns(self):

        self.df.columns = [
            str(col).strip().lower()
            for col in self.df.columns
        ]

    def _rename_columns(self):

        rename_map = {}

        for standard_name, aliases in self.COLUMN_ALIASES.items():

            for alias in aliases:

                if alias in self.df.columns:
                    rename_map[alias] = standard_name
                    break

        self.df.rename(columns=rename_map, inplace=True)

    def _parse_dates(self):

        if "date" not in self.df.columns:
            return

        self.df["date"] = pd.to_datetime(
            self.df["date"],
            errors="coerce",
            dayfirst=True
        )

    def _clean_amounts(self):

        for column in ["debit", "credit", "balance"]:

            if column not in self.df.columns:
                continue

            self.df[column] = (
                self.df[column]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("₹", "", regex=False)
                .str.strip()
            )

            self.df[column] = pd.to_numeric(
                self.df[column],
                errors="coerce"
            )