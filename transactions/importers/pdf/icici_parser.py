import io
import pdfplumber
import pandas as pd

from .generic_parser import GenericPDFParser


class ICICIParser(GenericPDFParser):

    def extract_rows(self):

        rows = []

        mapping = None

        with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:

            for page in pdf.pages:

                tables = page.extract_tables()

                if not tables:
                    continue

                for table in tables:

                    if not table:
                        continue

                    header_index = None

                    # Find the actual header row
                    for i, row in enumerate(table):

                        row_text = " ".join(
                            str(c or "").replace("\n", " ").lower()
                            for c in row
                        )

                        if (
                            "transaction remarks" in row_text
                            and
                            "withdrawal amount" in row_text
                        ):
                            header_index = i
                            break

                    # ------------------------
                    # First page
                    # ------------------------

                    if header_index is not None:

                        header = [
                            str(c or "").replace("\n", " ").strip().lower()
                            for c in table[header_index]
                        ]

                        mapping = {}

                        for idx, col in enumerate(header):

                            if "value date" in col:
                                mapping["date"] = idx

                            elif "transaction remarks" in col:
                                mapping["description"] = idx

                            elif "withdrawal amount" in col:
                                mapping["debit"] = idx

                            elif "deposit amount" in col:
                                mapping["credit"] = idx

                            elif "balance" in col:
                                mapping["balance"] = idx

                        data_rows = table[header_index + 1:]

                    else:

                        if mapping is None:
                            continue

                        data_rows = table

                    # ------------------------
                    # Read transactions
                    # ------------------------

                    for row in data_rows:

                        if not row:
                            continue

                        if len(row) < 8:
                            continue

                        date = row[mapping["date"]]

                        if not date:
                            continue

                        rows.append({

                            "date": date,

                            "description": row[mapping["description"]],

                            "debit": row[mapping["debit"]],

                            "credit": row[mapping["credit"]],

                            "balance": row[mapping["balance"]],

                        })

        print("ICICI ROWS :", len(rows))

        return rows