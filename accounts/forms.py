from django import forms
from django.contrib.auth.models import User


class SignupForm(forms.ModelForm):

    # User.email is optional at the model level, but email verification
    # (OTP) requires one — so the signup form must enforce it.
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "placeholder": "Enter email"
        }),
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Enter password"
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Confirm password"
        })
    )

    class Meta:

        model = User

        fields = [

            "username",

            "email",

            "password"

        ]

        widgets = {

            "username": forms.TextInput(attrs={
                "placeholder": "Enter username"
            }),

            "email": forms.EmailInput(attrs={
                "placeholder": "Enter email"
            }),

        }

    def clean(self):

        cleaned = super().clean()

        password = cleaned.get("password")

        confirm = cleaned.get("confirm_password")

        if password != confirm:

            raise forms.ValidationError(

                "Passwords do not match."

            )

        return cleaned