"""AI-powered investment suggestion service (Indian stock market focused)."""
import os
import json
import asyncio
from decimal import Decimal


# A curated static universe of popular Indian equities used as fallback/context for the AI.
INDIAN_STOCK_UNIVERSE = [
    {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Energy", "risk": "medium"},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT", "risk": "low"},
    {"symbol": "INFY", "name": "Infosys", "sector": "IT", "risk": "low"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking", "risk": "low"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking", "risk": "low"},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking", "risk": "medium"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom", "risk": "medium"},
    {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG", "risk": "low"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG", "risk": "low"},
    {"symbol": "LT", "name": "Larsen & Toubro", "sector": "Infrastructure", "risk": "medium"},
    {"symbol": "ASIANPAINT", "name": "Asian Paints", "sector": "Paints", "risk": "medium"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "Auto", "risk": "medium"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors", "sector": "Auto", "risk": "high"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharma", "sector": "Pharma", "risk": "medium"},
    {"symbol": "TITAN", "name": "Titan Company", "sector": "Consumer", "risk": "medium"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "sector": "NBFC", "risk": "high"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises", "sector": "Conglomerate", "risk": "high"},
    {"symbol": "WIPRO", "name": "Wipro", "sector": "IT", "risk": "medium"},
    {"symbol": "NIFTYBEES", "name": "Nippon India ETF Nifty BeES", "sector": "Index ETF", "risk": "low"},
    {"symbol": "GOLDBEES", "name": "Nippon India ETF Gold BeES", "sector": "Gold ETF", "risk": "low"},
]


def _fallback_suggestions(risk_profile: str, amount: float):
    """Deterministic fallback when the LLM is unavailable."""
    picks = {
        "low": ["NIFTYBEES", "HDFCBANK", "TCS", "ITC", "GOLDBEES"],
        "medium": ["RELIANCE", "INFY", "ICICIBANK", "LT", "TITAN"],
        "high": ["TATAMOTORS", "BAJFINANCE", "ADANIENT", "SBIN", "INFY"],
    }.get(risk_profile, ["NIFTYBEES", "HDFCBANK", "TCS", "ITC", "GOLDBEES"])

    alloc_pct = round(100 / len(picks), 2)
    out = []
    for sym in picks:
        stock = next((s for s in INDIAN_STOCK_UNIVERSE if s["symbol"] == sym), None)
        if not stock:
            continue
        out.append({
            "symbol": stock["symbol"],
            "name": stock["name"],
            "sector": stock["sector"],
            "action": "buy",
            "risk_level": stock["risk"],
            "time_horizon": "3-5 years" if risk_profile != "high" else "1-3 years",
            "target_allocation_pct": alloc_pct,
            "rationale": f"Solid {stock['sector']} exposure suited to a {risk_profile}-risk portfolio. "
                         f"Consider SIP of ₹{int(amount * alloc_pct / 100):,} for diversification.",
        })
    return out


def generate_ai_suggestions(user, risk_profile: str = "medium", amount: float = 50000.0, horizon: str = "3-5 years"):
    """Generate AI-powered Indian stock suggestions. Falls back to a static plan if LLM fails."""
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        return _fallback_suggestions(risk_profile, amount)

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception:
        return _fallback_suggestions(risk_profile, amount)

    system_msg = (
        "You are an SEBI-aware Indian equity research assistant. "
        "You give suggestions from NSE-listed stocks / ETFs only. "
        "Always return STRICT JSON with a top-level 'suggestions' array. "
        "Each suggestion has: symbol, name, sector, action (buy/hold/accumulate), "
        "risk_level (low/medium/high), time_horizon, target_allocation_pct (number, sum ~100), rationale (max 40 words). "
        "Never advise on derivatives or F&O. Add a note that this is educational, not financial advice."
    )

    universe_txt = ", ".join(f"{s['symbol']} ({s['sector']})" for s in INDIAN_STOCK_UNIVERSE)

    user_prompt = (
        f"Build a diversified Indian equity portfolio suggestion.\n"
        f"Risk profile: {risk_profile}\n"
        f"Amount to deploy: ₹{amount:,.0f}\n"
        f"Time horizon: {horizon}\n"
        f"Prefer symbols from this universe (but you may pick 4-6): {universe_txt}.\n"
        "Return JSON only, no prose."
    )

    async def _run():
        chat = LlmChat(
            api_key=api_key,
            session_id=f"invest-{user.id}",
            system_message=system_msg,
        ).with_model("gemini", "gemini-3-flash-preview")
        resp = await chat.send_message(UserMessage(text=user_prompt))
        return resp

    try:
        text = asyncio.run(_run())
        # Extract JSON
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("no json")
        data = json.loads(text[start:end + 1])
        suggestions = data.get("suggestions") or []
        cleaned = []
        for s in suggestions[:8]:
            cleaned.append({
                "symbol": str(s.get("symbol", "")).upper()[:32],
                "name": str(s.get("name", ""))[:200],
                "sector": str(s.get("sector", ""))[:64],
                "action": str(s.get("action", "buy")).lower()[:16],
                "risk_level": str(s.get("risk_level", "medium")).lower()[:10],
                "time_horizon": str(s.get("time_horizon", horizon))[:32],
                "target_allocation_pct": float(s.get("target_allocation_pct", 0) or 0),
                "rationale": str(s.get("rationale", ""))[:800],
            })
        if not cleaned:
            return _fallback_suggestions(risk_profile, amount)
        return cleaned
    except Exception:
        return _fallback_suggestions(risk_profile, amount)


def portfolio_summary(user):
    from .models import Holding
    holdings = Holding.objects.filter(user=user)
    invested = sum((h.invested_amount for h in holdings), Decimal("0"))
    current = sum((h.current_value for h in holdings), Decimal("0"))
    pnl = current - invested
    pnl_pct = (pnl / invested * 100) if invested else Decimal("0")

    # Allocation by asset type
    by_type = {}
    for h in holdings:
        by_type.setdefault(h.asset_type, Decimal("0"))
        by_type[h.asset_type] += h.current_value

    allocation = []
    for atype, val in by_type.items():
        pct = (val / current * 100) if current else Decimal("0")
        allocation.append({
            "type": atype,
            "value": float(val),
            "percent": float(round(pct, 2)),
        })

    return {
        "invested": float(invested),
        "current": float(current),
        "pnl": float(pnl),
        "pnl_percent": float(round(pnl_pct, 2)),
        "holding_count": holdings.count(),
        "allocation": allocation,
    }
