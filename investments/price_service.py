"""Live-price service for Indian equities / ETFs via Yahoo Finance public chart API.

Zero-auth, cached in-memory for 60s, batched, resilient.
Indian NSE symbols get the ".NS" suffix; users can also enter a Yahoo-native
symbol (e.g. "^NSEI" or "BTC-INR") and it will be used as-is.
"""
import time
from decimal import Decimal
import requests
import logging

logger = logging.getLogger(__name__)

# symbol (yahoo-style) -> {"price": float, "currency": str, "ts": float}
_CACHE: dict[str, dict] = {}
_TTL = 60  # seconds

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}


def to_yahoo_symbol(symbol: str, asset_type: str = "stock") -> str:
    """Map a user-entered symbol to a Yahoo Finance ticker.

    - Stocks / ETFs / mutual funds → append .NS if not already suffixed.
    - Crypto → append -INR.
    - Gold → default to GOLDBEES.NS (an NSE gold ETF) if no symbol supplied.
    """
    s = (symbol or "").strip().upper()
    if not s:
        return ""
    if asset_type == "crypto" and "-" not in s:
        return f"{s}-INR"
    if "." in s or "-" in s or "^" in s:
        return s
    if asset_type in ("stock", "etf", "mutual_fund", "gold"):
        return f"{s}.NS"
    return s


def fetch_price(yahoo_symbol: str) -> dict | None:
    """Return {'price': float, 'currency': str} for a Yahoo symbol, or None."""
    if not yahoo_symbol:
        return None

    now = time.time()
    cached = _CACHE.get(yahoo_symbol)
    if cached and (now - cached["ts"]) < _TTL:
        return {"price": cached["price"], "currency": cached["currency"]}

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    try:
        r = requests.get(url, headers=_HEADERS, params={"interval": "1d", "range": "1d"}, timeout=6)
        if r.status_code != 200:
            return None
        data = r.json()
        result = (data.get("chart") or {}).get("result") or []
        if not result:
            return None
        meta = result[0].get("meta") or {}
        price = meta.get("regularMarketPrice")
        currency = meta.get("currency", "INR")
        if price is None:
            return None
        _CACHE[yahoo_symbol] = {"price": float(price), "currency": currency, "ts": now}
        return {"price": float(price), "currency": currency}
    except Exception as e:
        logger.warning("fetch_price(%s) failed: %s", yahoo_symbol, e)
        return None


def refresh_user_holdings(user):
    """Fetch live prices for every holding and update `current_price`.

    Returns a summary dict with counts + a list of per-holding updates.
    """
    from .models import Holding

    holdings = list(Holding.objects.filter(user=user))
    updated = []
    failed = []

    for h in holdings:
        y_sym = to_yahoo_symbol(h.symbol, h.asset_type)
        info = fetch_price(y_sym)
        if not info:
            failed.append({"id": h.id, "symbol": h.symbol})
            continue
        new_price = Decimal(str(round(info["price"], 2)))
        h.current_price = new_price
        h.save(update_fields=["current_price", "updated_at"])
        updated.append({
            "id": h.id,
            "symbol": h.symbol,
            "yahoo_symbol": y_sym,
            "price": float(new_price),
            "current_value": float(h.current_value),
            "pnl": float(h.pnl),
            "pnl_percent": float(round(h.pnl_percent, 2)),
        })

    return {
        "success": True,
        "updated_count": len(updated),
        "failed_count": len(failed),
        "updated": updated,
        "failed": failed,
        "timestamp": int(time.time()),
    }
