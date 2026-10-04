"""
Transaction Pattern Database

These are transaction patterns rather than merchant names.
Pattern matching runs before merchant matching.
"""

TRANSACTION_PATTERNS = {

    # -----------------------
    # Salary
    # -----------------------

    "salary": "Salary",
    "payroll": "Salary",
    "salary credit": "Salary",
    "monthly salary": "Salary",

    # -----------------------
    # Refunds
    # -----------------------

    "refund": "Refund",
    "reversal": "Refund",
    "chargeback": "Refund",

    # -----------------------
    # Cash
    # -----------------------

    "atm wdl": "Cash Withdrawal",
    "cash withdrawal": "Cash Withdrawal",
    "atm withdrawal": "Cash Withdrawal",
    "cash dep": "Cash Deposit",
    "cash deposit": "Cash Deposit",

    # -----------------------
    # Transfers
    # -----------------------

    "self transfer": "Transfer",
    "fund transfer": "Transfer",
    "account transfer": "Transfer",
    "imps": "Transfer",
    "neft": "Transfer",
    "rtgs": "Transfer",

    # -----------------------
    # Loan / EMI
    # -----------------------

    "emi": "EMI / Loans",
    "loan": "EMI / Loans",
    "loan repayment": "EMI / Loans",
    "auto debit": "EMI / Loans",

    # -----------------------
    # Investment
    # -----------------------

    "interest credit": "Investment",
    "mutual fund": "Investment",
    "sip": "Investment",
    "dividend": "Investment",

    # -----------------------
    # Insurance
    # -----------------------

    "insurance premium": "Insurance",
    "premium": "Insurance",

    # -----------------------
    # Utility
    # -----------------------

    "electricity bill": "Bills & Utilities",
    "water bill": "Bills & Utilities",
    "gas bill": "Bills & Utilities",
    "mobile recharge": "Bills & Utilities",
    "broadband": "Bills & Utilities",

}
