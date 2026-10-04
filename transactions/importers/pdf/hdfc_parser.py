import io
import re

import pdfplumber

from .generic_parser import GenericPDFParser


class HDFCParser(GenericPDFParser):

    DATE_RE = re.compile(r"\d{2}/\d{2}/\d{2}")

    AMOUNT_RE = re.compile(r"\d[\d,]*\.\d{2}")

    def extract_rows(self):

        lines = self._extract_lines()

        transactions = self._merge_transactions(lines)

        print("RAW TRANSACTIONS :", len(transactions))

        rows = []

        for tx in transactions:

            row = self._parse_transaction(tx)

            if row:

                rows.append(row)

        print("PARSED ROWS :", len(rows))

        return rows

    def _extract_lines(self):

        lines = []

        with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:

            for page in pdf.pages:

                text = page.extract_text()

                if not text:
                    continue

                for line in text.splitlines():

                    line = " ".join(line.split())

                    if not line:
                        continue

                    if "STATEMENTOF ACCOUNT" in line:
                        continue

                    if "DATE NARRATION" in line:
                        continue

                    if line.startswith("PAGENO"):
                        continue

                    if line.startswith("ACCOUNTBRANCH"):
                        continue

                    if line.startswith("ADDRESS"):
                        continue

                    if line.startswith("CITY"):
                        continue

                    if line.startswith("STATEACCOUNTBRANCHGSTN"):
                        continue

                    if line.startswith("HDFCBANKLIMITED"):
                        continue

                    if line.startswith("*CLOSINGBALANCE"):
                        continue

                    if line.startswith("CONTENTSOFTHISSTATEMENT"):
                        continue

                    lines.append(line)

        return lines

    def _merge_transactions(self, lines):

        transactions = []

        current = ""

        for line in lines:

            if self.DATE_RE.match(line):

                if current:
                    transactions.append(current.strip())

                current = line

            else:

                if current:
                    current += " " + line

        if current:
            transactions.append(current.strip())

        return transactions

    def _parse_transaction(self, text):

        dates = self.DATE_RE.findall(text)

        amounts = self.AMOUNT_RE.findall(text)

        if len(dates) < 2:
            return None

        if len(amounts) < 2:
            return None

        transaction_date = dates[0]

        value_date = dates[1]

        balance = amounts[-1]

        amount = amounts[-2]

        description = text

        description = description.replace(transaction_date, "", 1)
        description = description.replace(value_date, "", 1)

        description = description.rsplit(balance, 1)[0]
        description = description.rsplit(amount, 1)[0]

        description = " ".join(description.split())

        debit = ""
        credit = ""

        amount_value = float(amount.replace(",", ""))
        balance_value = float(balance.replace(",", ""))

        # Guess transaction type from keywords first
        desc_upper = description.upper()

        credit_keywords = (
            "CR",
            "CREDIT",
            "IMPS",
            "NEFTCR",
            "RTGSCR",
            "SALARY",
            "INTEREST",
            "CASHDEP",
            "DEPOSIT",
        )

        if any(k in desc_upper for k in credit_keywords):
            credit = amount
        else:
            debit = amount

        return {
            "date": transaction_date,
            "description": description,
            "debit": debit,
            "credit": credit,
            "balance": balance,
        }