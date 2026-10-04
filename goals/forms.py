from django import forms
from .models import Goal

from transactions.models import Transaction
from transactions.models import TransactionCategory
from django.db.models import Q


class GoalForm(forms.ModelForm):

    class Meta:

        model = Goal

        fields = [
            "title",
            "goal_type",
            "target_amount",
            "current_amount",
            "monthly_target",
            "deadline",
            "priority",
            "status",
            "notes",
        ]

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "id": "goal-title",
                    "class": "goal-input",
                    "placeholder": "e.g. Buy Dream Bike",
                    "autocomplete": "off",
                }
            ),

            "goal_type": forms.Select(
                attrs={
                    "id": "goal-type",
                    "class": "goal-select",
                }
            ),

            "target_amount": forms.NumberInput(
                attrs={
                    "id": "goal-target",
                    "class": "goal-input",
                    "placeholder": "500000",
                    "min": "1",
                    "step": "0.01",
                }
            ),

            "current_amount": forms.NumberInput(
                attrs={
                    "id": "goal-current",
                    "class": "goal-input",
                    "placeholder": "25000",
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "monthly_target": forms.NumberInput(
                attrs={
                    "id": "goal-monthly",
                    "class": "goal-input",
                    "placeholder": "10000",
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "deadline": forms.DateInput(
                attrs={
                    "id": "goal-deadline",
                    "class": "goal-input",
                    "type": "date",
                }
            ),

            "priority": forms.Select(
                attrs={
                    "id": "goal-priority",
                    "class": "goal-select",
                }
            ),

            "status": forms.Select(
                attrs={
                    "id": "goal-status",
                    "class": "goal-select",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "id": "goal-notes",
                    "class": "goal-textarea",
                    "rows": 4,
                    "placeholder": "Add additional notes...",
                }
            ),

        }

    def clean(self):

        cleaned_data = super().clean()

        target = cleaned_data.get("target_amount")

        current = cleaned_data.get("current_amount")

        monthly = cleaned_data.get("monthly_target")

        if target is not None and target <= 0:

            self.add_error(
                "target_amount",
                "Target amount must be greater than zero."
            )

        if current is not None and current < 0:

            self.add_error(
                "current_amount",
                "Current savings cannot be negative."
            )

        if (
            target is not None and
            current is not None and
            current > target
        ):

            self.add_error(
                "current_amount",
                "Current savings cannot exceed target amount."
            )

        if monthly is not None and monthly < 0:

            self.add_error(
                "monthly_target",
                "Monthly target cannot be negative."
            )

        return cleaned_data

class GoalContributionForm(forms.Form):

    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        label="Contribution Amount",
        widget=forms.NumberInput(
            attrs={
                "class": "goal-input",
                "placeholder": "10000",
                "step": "0.01",
                "min": "0.01",
            }
        ),
    )

    category = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(
            attrs={
                "class": "goal-select",
            }
        ),
    )

    payment_method = forms.ChoiceField(
        choices=Transaction.PAYMENT_METHODS,
        widget=forms.Select(
            attrs={
                "class": "goal-select",
            }
        ),
    )

    transaction_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "class": "goal-input",
                "type": "date",
            }
        ),
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "goal-textarea",
                "rows": 3,
                "placeholder": "Monthly contribution...",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = (
            TransactionCategory.objects.filter(
                Q(user=user) | Q(is_default=True),
                category_type="expense",
            ).order_by("name")
        )