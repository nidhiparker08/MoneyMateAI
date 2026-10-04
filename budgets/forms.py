from django import forms

from .models import Budget
from transactions.models import TransactionCategory


class BudgetForm(forms.ModelForm):

    class Meta:
        model = Budget
        fields = [
            "category",
            "amount",
            "month",
            "year",
        ]

        widgets = {
            "category": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Budget Amount"
                }
            ),
            "month": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),
            "year": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Year"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        if user:
            self.fields["category"].queryset = (
                TransactionCategory.objects
                .filter(
                    user=user,
                    category_type="expense",
                )
                .order_by("name")
            )