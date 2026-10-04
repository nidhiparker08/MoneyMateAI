import io
import pdfplumber

from .pdf.bank_detector import BankDetector

from .pdf.generic_parser import GenericPDFParser
from .pdf.sbi_parser import SBIParser
from .pdf.hdfc_parser import HDFCParser
from .pdf.icici_parser import ICICIParser


class PDFImporter:

    def __init__(self, uploaded_file):

        self.uploaded_file = uploaded_file

    def parse(self):

        pdf_bytes = self.uploaded_file.read()

        detector = BankDetector(pdf_bytes)

        bank = detector.detect()

        print("=" * 50)
        print("BANK DETECTED :", bank)
        print("=" * 50)

        parser = self._get_parser(

            bank,

            pdf_bytes,

        )

        return parser.parse()

    def _get_parser(

        self,

        bank,

        pdf_bytes,

    ):

        if bank == "SBI":

            return SBIParser(pdf_bytes)

        elif bank == "HDFC":

            return HDFCParser(pdf_bytes)

        elif bank == "ICICI":

            return ICICIParser(pdf_bytes)

        else:

            return GenericPDFParser(pdf_bytes)