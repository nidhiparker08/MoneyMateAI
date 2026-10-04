from decimal import Decimal
from django.db import models
from django.conf import settings


class Holding(models.Model):
    """A single investment holding in the user's portfolio (Indian equities/mutual funds/gold/crypto)."""

    ASSET_TYPES = [
        ("stock", "Stock"),
        ("mutual_fund", "Mutual Fund"),
        ("etf", "ETF"),
        ("gold", "Gold"),
        ("crypto", "Crypto"),
        ("bond", "Bond"),
        ("fd", "Fixed Deposit"),
    ]

    RISK_LEVELS = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    symbol = models.CharField(max_length=32)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES, default="stock")
    sector = models.CharField(max_length=64, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    buy_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    current_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default="medium")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.symbol} ({self.quantity})"

    @property
    def invested_amount(self):
        return (self.buy_price or Decimal("0")) * (self.quantity or Decimal("0"))

    @property
    def current_value(self):
        return (self.current_price or Decimal("0")) * (self.quantity or Decimal("0"))

    @property
    def pnl(self):
        return self.current_value - self.invested_amount

    @property
    def pnl_percent(self):
        inv = self.invested_amount
        if inv == 0:
            return Decimal("0")
        return (self.pnl / inv) * Decimal("100")


class InvestmentSuggestion(models.Model):
    """AI-generated investment suggestions for the user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="investment_suggestions",
    )
    symbol = models.CharField(max_length=32)
    name = models.CharField(max_length=200)
    sector = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=16, default="buy")  # buy / hold / sell / accumulate
    rationale = models.TextField()
    risk_level = models.CharField(max_length=10, default="medium")
    time_horizon = models.CharField(max_length=32, default="Long term")
    target_allocation_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.symbol} — {self.action}"
