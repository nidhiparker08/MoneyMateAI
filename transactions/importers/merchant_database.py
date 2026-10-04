"""
Merchant → Category Mapping

Keys should always be lowercase because
MerchantCleaner returns lowercase text.
"""

MERCHANT_CATEGORIES = {

    # =========================
    # FOOD & DINING
    # =========================
    "coffee shop": "Food & Dining",
    "cafe": "Food & Dining",
    "restaurant": "Food & Dining",
    "hotel": "Food & Dining",
    "food court": "Food & Dining",
    "zomato": "Food & Dining",
    "swiggy": "Food & Dining",
    "dominos": "Food & Dining",
    "pizza hut": "Food & Dining",
    "kfc": "Food & Dining",
    "burger king": "Food & Dining",
    "mcdonald": "Food & Dining",
    "subway": "Food & Dining",
    "starbucks": "Food & Dining",

    # =========================
    # SHOPPING
    # =========================
    "amazon": "Shopping",
    "flipkart": "Shopping",
    "myntra": "Shopping",
    "ajio": "Shopping",
    "meesho": "Shopping",
    "shopping": "Shopping",

    # =========================
    # TRANSPORT
    # =========================
    "fuel": "Transportation",
    "petrol": "Transportation",
    "petrol pump": "Transportation",
    "diesel": "Transportation",
    "metro": "Transportation",
    "metro recharge": "Transportation",
    "uber": "Transportation",
    "ola": "Transportation",
    "rapido": "Transportation",

    # =========================
    # BILLS
    # =========================
    "electricity": "Bills & Utilities",
    "electricity bill": "Bills & Utilities",
    "water bill": "Bills & Utilities",
    "internet": "Bills & Utilities",
    "internet bill": "Bills & Utilities",
    "mobile recharge": "Bills & Utilities",
    "recharge": "Bills & Utilities",
    "jio": "Bills & Utilities",
    "airtel": "Bills & Utilities",
    "vi": "Bills & Utilities",

    # =========================
    # HEALTH
    # =========================
    "medical": "Health & Medical",
    "medical store": "Health & Medical",
    "pharmacy": "Health & Medical",
    "chemist": "Health & Medical",
    "apollo": "Health & Medical",
    "medplus": "Health & Medical",

    # =========================
    # ENTERTAINMENT
    # =========================
    "movie": "Entertainment",
    "movie tickets": "Entertainment",
    "cinema": "Entertainment",
    "bookmyshow": "Entertainment",
    "netflix": "Entertainment",
    "spotify": "Entertainment",

    # =========================
    # INCOME
    # =========================
    "salary": "Salary",
    "payroll": "Salary",
    "freelance": "Freelance Income",

    # =========================
    # REFUND
    # =========================
    "refund": "Refund",
}