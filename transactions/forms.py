from django import forms
from django.db.models import Q
from django.utils import timezone

from .models import Transaction
from goals.models import Goal


class TransactionForm(forms.ModelForm):

    transaction_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        )
    )

    transaction_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(
            attrs={
                "type": "time",
                "class": "form-control",
            }
        )
    )

    goal = forms.ModelChoiceField(

        queryset=Goal.objects.none(),

        required=False,

        empty_label="No Goal Contribution",

        widget=forms.Select(

            attrs={

                "class": "form-select",

                "id": "goal-select",

            }

        ),

    )

    class Meta:

        model = Transaction

        fields = [

            "title",

            "merchant",

            "transaction_type",

            "amount",

            "category",

            "goal",

            "payment_method",

            "transaction_date",

            "transaction_time",

            "notes",

        ]

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Transaction title",
                }
            ),

            "merchant": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Merchant (optional)",
                }
            ),

            "transaction_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Amount",
                }
            ),

            "category": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "payment_method": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Additional notes...",
                }
            ),

        }

    def __init__(self, *args, **kwargs):

        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        if user:

            self.fields["category"].queryset = (
                self.fields["category"]
                .queryset
                .filter(user=user)
                .order_by("category_type", "name")
            )

            self.fields["goal"].queryset = Goal.objects.filter(

                user=user,

                status="active",

            ).order_by("deadline")

    def clean(self):

        cleaned_data = super().clean()

        transaction_date = cleaned_data.get("transaction_date")

        transaction_time = cleaned_data.get("transaction_time")

        if transaction_date is not None:

            today = timezone.localdate()

            if transaction_date > today:

                self.add_error(
                    "transaction_date",
                    "Transaction date cannot be in the future.",
                )

            elif (
                transaction_date == today
                and transaction_time is not None
                and transaction_time > timezone.localtime().time()
            ):

                self.add_error(
                    "transaction_time",
                    "Transaction time cannot be in the future.",
                )

        return cleaned_data