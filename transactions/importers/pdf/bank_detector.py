import io
import pdfplumber


class BankDetector:
    """
    Detects the bank from the first page(s) of a PDF
    and returns the parser class that should handle it.
    """

    BANKS = {

        "HDFC": [

            "HDFC BANK",

            "HDFC BANK LIMITED",

            "HDFCBANK",

            "STATEMENTOF ACCOUNT",

            "CLOSINGBALANCE",

            "VALUEDT",

        ],

        "SBI": [

            "STATE BANK OF INDIA",

            "STATE BANK",

        ],

        "ICICI": [

            "ICICI BANK",

            "TRANSACTIONS LIST",

            "TRANSACTION REMARKS",

            "WITHDRAWAL AMOUNT",

            "DEPOSIT AMOUNT",

        ],

    }

    def __init__(self, pdf_bytes):

        self.pdf_bytes = pdf_bytes

    def detect(self):

        with pdfplumber.open(

            io.BytesIO(self.pdf_bytes)

        ) as pdf:

            text = ""

            for page in pdf.pages[:2]:

                extracted = page.extract_text()

                if extracted:

                    text += extracted.upper()

        print("\n========== PDF TEXT ==========\n")
        print(text[:3000])   # Print first 3000 characters
        print("\n==============================\n")

        for bank, keywords in self.BANKS.items():

            for keyword in keywords:

                if keyword in text:

                    return bank

        return "GENERIC"