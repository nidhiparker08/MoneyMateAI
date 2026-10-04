import os

from .csv_importer import CSVImporter
from .excel_importer import ExcelImporter
from .pdf_importer import PDFImporter
from .duplicate_checker import DuplicateChecker


class StatementDetector:

    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file

    def parse(self, user):

        extension = os.path.splitext(
            self.uploaded_file.name
        )[1].lower()

        if extension == ".csv":

            transactions = CSVImporter(
                self.uploaded_file, user=user
            ).parse()

        elif extension in [".xlsx", ".xls"]:

            transactions = ExcelImporter(
                self.uploaded_file, user=user
            ).parse()

        elif extension == ".pdf":

            transactions = PDFImporter(
                self.uploaded_file
            ).parse()

        else:

            raise ValueError(
                "Only CSV, Excel, and text-based PDF statements are supported."
            )

        transactions = DuplicateChecker.mark_duplicates(
            user,
            transactions
        )

        return transactions
