import re


class MerchantCleaner:
    """
    Cleans transaction descriptions before categorization.

    Example:
    UPI-12345-ZOMATO PAYMENT
        ↓
    zomato

    POS AMAZON PAY INDIA
        ↓
    amazon

    IMPS TO ABC STORE
        ↓
    abc store
    """

    REMOVE_WORDS = [
        "upi",
        "imps",
        "neft",
        "rtgs",
        "pos",
        "atm",
        "txn",
        "payment",
        "transfer",
        "credited",
        "debited",
        "by",
        "to",
        "ref",
        "upiid",
        "upi/",
        "upi-",
        "upi:",
        "india",
        "pvt",
        "ltd",
        "private",
        "limited",
    ]

    @classmethod
    def clean(cls, description):

        if not description:
            return ""

        text = str(description).lower()

        # Replace symbols with spaces
        text = re.sub(r"[^\w\s]", " ", text)

        # Remove numbers
        text = re.sub(r"\d+", " ", text)

        # Remove common banking words
        for word in cls.REMOVE_WORDS:
            text = re.sub(rf"\b{re.escape(word)}\b", " ", text)

        # Remove extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        # -------------------------
        # Normalization Rules
        # -------------------------

        replacements = {

            "coffee shop": "coffee shop",
            "coffee": "coffee shop",
            "cafe": "coffee shop",

            "medical s re": "medical store",
            "medical store": "medical store",
            "chemist": "medical store",
            "pharmacy": "medical store",

            "fuel station": "fuel",
            "petrol pump": "fuel",
            "diesel pump": "fuel",

            "electricity": "electricity bill",
            "power bill": "electricity bill",

            "internet": "internet bill",
            "broadband": "internet bill",

            "movie": "movie tickets",
            "cinema": "movie tickets",

            "metro": "metro recharge",

        }

        for old, new in replacements.items():

            if old in text:
                return new

        return text
