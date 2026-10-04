import io
import pdfplumber

from .generic_parser import GenericPDFParser


class SBIParser(GenericPDFParser):

    def extract_rows(self):

        rows = []

        with pdfplumber.open(
            io.BytesIO(self.pdf_bytes)
        ) as pdf:

            for page in pdf.pages:

                tables = page.extract_tables()

                print(f"\nSBI PAGE {page.page_number}")
                print(f"TABLES FOUND: {len(tables)}")

                for i, table in enumerate(tables):

                    print(f"\nTABLE {i}")

                    print("ROWS:", len(table))

                    if table:

                        print("FIRST ROW:", table[0])

        return rows