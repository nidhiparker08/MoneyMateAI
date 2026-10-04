from django.urls import path
from . import views

app_name = "transactions"

urlpatterns = [

    # ======================================================
    # Transactions Page
    # ======================================================

    path(
        "",
        views.transactions_page,
        name="index",
    ),

    # ======================================================
    # Create Transaction
    # ======================================================

    path(
        "create/",
        views.create_transaction,
        name="create",
    ),

    # ======================================================
    # Get Transaction
    # ======================================================

    path(
        "<int:transaction_id>/",
        views.get_transaction,
        name="get",
    ),

    # ======================================================
    # Update Transaction
    # ======================================================

    path(
        "update/<int:transaction_id>/",
        views.update_transaction,
        name="update",
    ),

    # ======================================================
    # Delete Transaction
    # ======================================================

    path(
        "delete/<int:transaction_id>/",
        views.delete_transaction,
        name="delete",
    ),

    # ======================================================
    # Connect Bank (BankHub)
    # ======================================================

    path(
        "connect-bank/",
        views.connect_bank,
        name="connect_bank",
    ),

]