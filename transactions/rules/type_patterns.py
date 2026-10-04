"""
Transaction Type Patterns (regex + keyword).

Used by TransactionIntelligence to produce a fine-grained
`transaction_type_detail` value.

Do NOT map every merchant here — merchant mappings live in
`merchant_database.py`. This file is only for STRONG signals
that determine the DETAILED transaction type.

Format:
    (compiled_regex, transaction_type_detail, subcategory, confidence)

The list is walked top-to-bottom, first strong hit wins.
"""

import re

# ----------------------------------------------------------------
# Type constants (matches the 17 detailed types requested)
# ----------------------------------------------------------------

# income-side
T_SALARY            = "salary"
T_INTEREST          = "interest"
T_DIVIDEND          = "dividend"
T_CASHBACK          = "cashback"
T_REFUND            = "refund"
T_INCOME            = "income"          # generic

# expense-side
T_INVESTMENT        = "investment"
T_GOAL_CONTRIB      = "goal_contribution"
T_INSURANCE         = "insurance"
T_LOAN_EMI          = "loan_emi"
T_SUBSCRIPTION      = "subscription"
T_UTILITY_BILL      = "utility_bill"
T_TAX               = "tax"
T_EXPENSE           = "expense"         # generic

# transfer-like (direction depends on debit/credit)
T_INTERNAL_TRANSFER = "internal_transfer"
T_FRIEND_TRANSFER   = "friend_transfer"
T_BUSINESS_TRANSFER = "business_transfer"

# ----------------------------------------------------------------
# Rule table: (regex, type_detail, subcategory, confidence)
# ----------------------------------------------------------------

_R = re.compile

TYPE_RULES = [

    # ---------- Salary ----------
    (_R(r"\b(salary|payroll|salary\s*credit|monthly\s*salary|sal\s*cr|neft.*salary)\b", re.I),
     T_SALARY, "Salary", 96),

    # ---------- Dividend ----------
    (_R(r"\b(dividend|div\s*payout|equity\s*dividend|dividend\s*payout|div\s*cr)\b", re.I),
     T_DIVIDEND, "Dividend", 95),

    # ---------- Interest ----------
    (_R(r"\b(interest\s*credit|int\.?\s*credit|fd\s*interest|sb\s*int|interest\s*paid)\b", re.I),
     T_INTEREST, "Interest", 94),

    # ---------- Cashback ----------
    (_R(r"\b(cashback|cash\s*back|reward\s*credit)\b", re.I),
     T_CASHBACK, "Cashback", 96),

    # ---------- Refund ----------
    (_R(r"\b(refund|reversal|chargeback|refunded|amount\s*reversed)\b", re.I),
     T_REFUND, "Refund", 95),

    # ---------- Investment / SIP / MF / stocks ----------
    (_R(r"\b(sip|mutual\s*fund|mf\s*(purchase|buy)|zerodha|groww|upstox|"
        r"kotak\s*mf|hdfc\s*amc|icici\s*pru|sbi\s*mf|axis\s*mf|nippon\s*mf|"
        r"mirae|dsp|quant\s*mf|paras\s*mf|kuvera|coin\.zerodha|angelone|angel\s*one)\b", re.I),
     T_INVESTMENT, "Mutual Fund / Stocks", 96),

    (_R(r"\b(nps\s*contribution|nps\s*trust|nse\s*clearing|bse\s*clearing|"
        r"stock\s*purchase|equity\s*purchase|shares?\s*purchase)\b", re.I),
     T_INVESTMENT, "Equity", 94),

    # ---------- Insurance ----------
    (_R(r"\b(insurance\s*premium|policy\s*premium|life\s*insurance|"
        r"health\s*insurance|term\s*plan|lic|licindia|hdfc\s*ergo|"
        r"star\s*health|max\s*bupa|niva\s*bupa|acko|policybazaar|premium\s*paid)\b", re.I),
     T_INSURANCE, "Insurance Premium", 94),

    # ---------- Loan / EMI ----------
    (_R(r"\b(emi|loan\s*repayment|loan\s*emi|home\s*loan|car\s*loan|"
        r"personal\s*loan|auto\s*debit\s*emi|nach\s*emi|loan\s*disbursal)\b", re.I),
     T_LOAN_EMI, "EMI / Loan", 95),

    # ---------- Subscription ----------
    (_R(r"\b(netflix|prime\s*video|amazon\s*prime|hotstar|jiocinema|"
        r"zee5|sonyliv|apple\s*music|spotify|youtube\s*premium|"
        r"google\s*one|icloud|dropbox|adobe|canva|figma|notion|"
        r"chatgpt\s*plus|openai|github|linkedin\s*premium|coursera|udemy)\b", re.I),
     T_SUBSCRIPTION, "Streaming / Software", 92),

    # ---------- Utility bill ----------
    (_R(r"\b(electricity\s*bill|power\s*bill|bescom|torrent\s*power|"
        r"reliance\s*energy|tata\s*power|water\s*bill|gas\s*bill|"
        r"piped\s*gas|adani\s*gas|mahanagar\s*gas|internet\s*bill|"
        r"broadband\s*bill|act\s*fibernet|jio\s*fiber|airtel\s*xstream|"
        r"mobile\s*recharge|dth\s*recharge|d2h\s*recharge|tata\s*sky)\b", re.I),
     T_UTILITY_BILL, "Utility", 93),

    # ---------- Tax ----------
    (_R(r"\b(income\s*tax|tds|advance\s*tax|self\s*assessment\s*tax|"
        r"gst\s*payment|challan|tax\s*payment|itr\s*refund)\b", re.I),
     T_TAX, "Tax", 92),

    # ---------- Internal / Self transfer ----------
    (_R(r"\b(self\s*transfer|own\s*account|to\s*self|to\s*own|"
        r"own\s*a/c|transfer\s*to\s*self|self\s*a/c)\b", re.I),
     T_INTERNAL_TRANSFER, "Self Transfer", 95),

    # Generic transfer channel — direction TBD later.
    (_R(r"\b(imps|neft|rtgs|fund\s*transfer|acc?ount\s*transfer|"
        r"upi\s*transfer|p2a|p2m)\b", re.I),
     "transfer", "Bank Transfer", 55),
]


# ----------------------------------------------------------------
# Payment-method detection from raw description.
# ----------------------------------------------------------------

PAYMENT_METHOD_RULES = [
    (_R(r"\bupi\b|@[a-z]+", re.I),                       "upi"),
    (_R(r"\b(imps|neft|rtgs|net\s*banking|netbanking)\b", re.I), "net_banking"),
    (_R(r"\bcredit\s*card\b|\bcc\s*payment\b",           re.I), "credit_card"),
    (_R(r"\bdebit\s*card\b|pos\s+", re.I),               "debit_card"),
    (_R(r"\bcheque\b|\bchq\b",                            re.I), "cheque"),
    (_R(r"\bcash\b|atm\s*(wdl|withdrawal|deposit)\b",     re.I), "cash"),
]


# ----------------------------------------------------------------
# Subcategory extras — small overlay on top of MERCHANT_CATEGORIES.
# ----------------------------------------------------------------

SUBCATEGORY_MAP = {
    # Food & Dining
    "zomato": "Food Delivery",
    "swiggy": "Food Delivery",
    "dominos": "Fast Food",
    "pizza hut": "Fast Food",
    "kfc": "Fast Food",
    "burger king": "Fast Food",
    "mcdonald": "Fast Food",
    "starbucks": "Coffee",
    "cafe": "Coffee",
    "coffee shop": "Coffee",

    # Shopping
    "amazon": "Online Shopping",
    "flipkart": "Online Shopping",
    "myntra": "Apparel",
    "ajio": "Apparel",
    "meesho": "Online Shopping",

    # Transport
    "uber": "Ride Hailing",
    "ola": "Ride Hailing",
    "rapido": "Ride Hailing",
    "petrol": "Fuel",
    "diesel": "Fuel",
    "fuel": "Fuel",
    "metro": "Public Transit",

    # Bills
    "jio": "Mobile",
    "airtel": "Mobile",
    "vi": "Mobile",
    "electricity": "Electricity",

    # Investment / MF houses (subcategory refinement)
    "zerodha": "Equity Broker",
    "groww": "Investment Platform",
    "upstox": "Equity Broker",
    "angelone": "Equity Broker",
    "angel one": "Equity Broker",
    "kuvera": "Investment Platform",

    # Insurance
    "lic": "Life Insurance",
    "hdfc ergo": "General Insurance",
    "star health": "Health Insurance",
    "niva bupa": "Health Insurance",
    "acko": "General Insurance",
}
