from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import TransactionCategory


DEFAULT_CATEGORIES = {

    "income": [

        "Salary",
        "Business",
        "Freelance",
        "Bonus",
        "Interest",
        "Dividend",
        "Refund",
        "Gift",

    ],

    "expense": [

        "Food",
        "Groceries",
        "Shopping",
        "Fuel",
        "Transport",
        "Rent",
        "Utilities",
        "Bills",
        "Healthcare",
        "Education",
        "Entertainment",
        "Travel",
        "Insurance",
        "EMI",
        "Taxes",
        "Other",

    ],

}


@receiver(post_save, sender=User)
def create_default_categories(sender, instance, created, **kwargs):

    if not created:
        return

    for category_type, categories in DEFAULT_CATEGORIES.items():

        for category in categories:

            TransactionCategory.objects.get_or_create(
                user=instance,
                name=category,
                category_type=category_type,
                defaults={
                    "is_default": False,
                },
            )