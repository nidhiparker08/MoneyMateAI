from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import HoldingForm
from .models import Holding, InvestmentSuggestion
from .price_service import fetch_price, to_yahoo_symbol, refresh_user_holdings
from .services import (
    INDIAN_STOCK_UNIVERSE,
    generate_ai_suggestions,
    portfolio_summary,
)


@login_required
def investments_page(request):
    holdings = Holding.objects.filter(user=request.user)

    # Auto-refresh prices if any holding hasn't been updated in >10 minutes.
    from datetime import timedelta
    from django.utils import timezone
    if holdings.exists():
        stale = holdings.filter(
            updated_at__lt=timezone.now() - timedelta(minutes=10)
        ).exists() or holdings.filter(current_price=0).exists()
        if stale:
            try:
                refresh_user_holdings(request.user)
                holdings = Holding.objects.filter(user=request.user)
            except Exception:
                pass

    summary = portfolio_summary(request.user)
    suggestions = InvestmentSuggestion.objects.filter(
        user=request.user
    )[:8]

    latest_updated = holdings.order_by("-updated_at").first()
    context = {
        "active_page": "investments",
        "holdings": holdings,
        "summary": summary,
        "suggestions": suggestions,
        "form": HoldingForm(),
        "stock_universe": INDIAN_STOCK_UNIVERSE,
        "prices_last_updated": latest_updated.updated_at if latest_updated else None,
    }
    return render(request, "investments/investments.html", context)


@login_required
@require_POST
def refresh_prices(request):
    """Fetch live prices from Yahoo Finance for all of the user's holdings."""
    try:
        result = refresh_user_holdings(request.user)
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)
    result["summary"] = portfolio_summary(request.user)
    return JsonResponse(result)


@login_required
def quote(request):
    """Live price lookup for a single symbol — used by the Add-Holding form."""
    symbol = request.GET.get("symbol", "")
    asset_type = request.GET.get("asset_type", "stock")
    y = to_yahoo_symbol(symbol, asset_type)
    info = fetch_price(y)
    if not info:
        return JsonResponse({"success": False, "symbol": symbol, "yahoo": y}, status=404)
    return JsonResponse({
        "success": True,
        "symbol": symbol.upper(),
        "yahoo_symbol": y,
        "price": info["price"],
        "currency": info["currency"],
    })


@login_required
@require_POST
def add_holding(request):
    form = HoldingForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {"success": False, "errors": form.errors},
            status=400,
        )
    h = form.save(commit=False)
    h.user = request.user
    if not h.current_price:
        # Try live fetch first, else fall back to buy_price.
        info = fetch_price(to_yahoo_symbol(h.symbol, h.asset_type))
        if info:
            from decimal import Decimal
            h.current_price = Decimal(str(round(info["price"], 2)))
        else:
            h.current_price = h.buy_price
    h.save()
    return JsonResponse({
        "success": True,
        "message": "Holding added successfully.",
        "id": h.id,
    })


@login_required
@require_POST
def delete_holding(request, pk):
    holding = get_object_or_404(Holding, pk=pk, user=request.user)
    holding.delete()
    return JsonResponse({"success": True})


@login_required
@require_POST
def generate_suggestions(request):
    risk = request.POST.get("risk", "medium")
    try:
        amount = float(request.POST.get("amount", 50000))
    except (TypeError, ValueError):
        amount = 50000.0
    horizon = request.POST.get("horizon", "3-5 years")

    # Wipe old suggestions for this user before regenerating.
    InvestmentSuggestion.objects.filter(user=request.user).delete()

    ai = generate_ai_suggestions(
        request.user,
        risk_profile=risk,
        amount=amount,
        horizon=horizon,
    )

    created = []
    for s in ai:
        obj = InvestmentSuggestion.objects.create(
            user=request.user,
            symbol=s["symbol"],
            name=s["name"],
            sector=s.get("sector", ""),
            action=s.get("action", "buy"),
            rationale=s.get("rationale", ""),
            risk_level=s.get("risk_level", "medium"),
            time_horizon=s.get("time_horizon", horizon),
            target_allocation_pct=s.get("target_allocation_pct", 0),
        )
        created.append({
            "id": obj.id,
            "symbol": obj.symbol,
            "name": obj.name,
            "sector": obj.sector,
            "action": obj.action,
            "rationale": obj.rationale,
            "risk_level": obj.risk_level,
            "time_horizon": obj.time_horizon,
            "target_allocation_pct": float(obj.target_allocation_pct),
        })

    return JsonResponse({
        "success": True,
        "suggestions": created,
        "message": f"Generated {len(created)} AI suggestions.",
    })
