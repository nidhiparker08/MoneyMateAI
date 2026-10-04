"""
Receiver / counter-party extraction patterns.

Given a raw description like:
    "UPI/123456/TO ANITA SHARMA/OKHDFCBANK"
    "IMPS-P2A 987654 CR TO RAM ENTERPRISES"
    "NEFT TO ACME CORP PVT LTD"

we want to pull out the recipient name.
"""

import re

# Ordered list of regex patterns. First hit wins.
RECEIVER_PATTERNS = [
    # "TO <NAME>/..." or "TO <NAME>-..." — commonest UPI form
    re.compile(r"\b(?:to|paid\s*to|txn\s*to)\s+([A-Za-z][A-Za-z0-9 &.\-']{2,60}?)(?:\s*(?:/|-|\||upi|@|ref|txn)|$)", re.I),

    # "IMPS/TO <NAME>"
    re.compile(r"imps[/ -]+(?:p2a|p2m)?[/ -]*([A-Za-z][A-Za-z0-9 &.\-']{2,60}?)(?:\s*(?:/|-|\|)|$)", re.I),

    # "NEFT-<NAME>-..."
    re.compile(r"(?:neft|rtgs)[/ -]+(?:tr[fn]?|to)?[/ -]*([A-Za-z][A-Za-z0-9 &.\-']{2,60}?)(?:\s*(?:/|-|\|)|$)", re.I),

    # "UPI-<NAME>-..."
    re.compile(r"upi[/ -]+(?:[0-9]+[/ -]+)?([A-Za-z][A-Za-z0-9 &.\-']{2,60}?)(?:\s*(?:/|-|\||@)|$)", re.I),
]


# ----------------------------------------------------------------
# Heuristics to sub-classify a generic transfer as
# internal / friend / business.
# ----------------------------------------------------------------

# Business suffixes (Indian corporate forms)
BUSINESS_SUFFIXES = [
    "pvt ltd", "private limited", "limited", "ltd", "llp", "inc",
    "corp", "corporation", "enterprises", "enterprise", "co.",
    "traders", "trading", "services", "solutions", "technologies",
    "industries", "constructions", "developers", "estate",
    "and sons", "& sons", "and co", "& co", "hotels", "restaurants",
    "stores", "mart", "supermarket", "bakery",
]

# Words that indicate the user's own account (self transfer)
SELF_HINTS = [
    "self", "own account", "own a/c", "myself", "to self",
]


def looks_like_business(name: str) -> bool:
    if not name:
        return False
    n = name.lower()
    return any(suffix in n for suffix in BUSINESS_SUFFIXES)


def looks_like_self(description: str, name: str = "") -> bool:
    text = (description + " " + (name or "")).lower()
    return any(h in text for h in SELF_HINTS)


def extract_receiver(description: str) -> str:
    """Return a best-effort clean receiver name, or '' if none found."""
    if not description:
        return ""

    for pattern in RECEIVER_PATTERNS:
        m = pattern.search(description)
        if not m:
            continue
        name = (m.group(1) or "").strip(" -/:.|")
        if not name:
            continue
        # Reject if it's obviously a code (all digits, or contains 'UPI' etc.)
        stripped = re.sub(r"[^A-Za-z]", "", name)
        if len(stripped) < 3:
            continue
        # Reject noisy tails
        junk = {"ref", "txn", "upi", "imps", "neft", "rtgs", "bank", "hdfc",
                "sbi", "icici", "axis", "kotak", "yesbank", "yes bank"}
        low = name.lower()
        if any(low == j or low.startswith(j + " ") for j in junk):
            continue
        # Title-case, collapse spaces
        cleaned = re.sub(r"\s+", " ", name).title()
        # Cap length
        return cleaned[:120]
    return ""
