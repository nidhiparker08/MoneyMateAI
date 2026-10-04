from django import forms
from .models import Holding


class HoldingForm(forms.ModelForm):
    class Meta:
        model = Holding
        fields = [
            "symbol", "name", "asset_type", "sector",
            "quantity", "buy_price", "current_price",
            "risk_level", "notes",
        ]
        widgets = {
            "symbol": forms.TextInput(attrs={"class": "inv-input", "placeholder": "e.g. RELIANCE"}),
            "name": forms.TextInput(attrs={"class": "inv-input", "placeholder": "Reliance Industries"}),
            "asset_type": forms.Select(attrs={"class": "inv-select"}),
            "sector": forms.TextInput(attrs={"class": "inv-input", "placeholder": "Energy / IT / Banking..."}),
            "quantity": forms.NumberInput(attrs={"class": "inv-input", "step": "0.0001", "min": "0"}),
            "buy_price": forms.NumberInput(attrs={"class": "inv-input", "step": "0.01", "min": "0"}),
            "current_price": forms.NumberInput(attrs={"class": "inv-input", "step": "0.01", "min": "0"}),
            "risk_level": forms.Select(attrs={"class": "inv-select"}),
            "notes": forms.Textarea(attrs={"class": "inv-input", "rows": 3, "placeholder": "Optional notes..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Current price is optional — it's auto-fetched from Yahoo Finance if omitted.
        self.fields["current_price"].required = False
        self.fields["sector"].required = False
        self.fields["notes"].required = False
