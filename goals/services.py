from decimal import Decimal

from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404

from .models import Goal

from transactions.services import TransactionService


class GoalContributionService:

    @staticmethod
    @db_transaction.atomic
    def add_contribution(
        *,
        user,
        goal_id,
        amount,
        transaction_date,
        payment_method,
        category,
        title="Goal Contribution",
        merchant="",
        notes="",
    ):

        goal = get_object_or_404(

            Goal,

            id=goal_id,

            user=user,

            status="active",

        )

        transaction = TransactionService.create_transaction(

            user=user,

            title=title,

            merchant=merchant,

            amount=amount,

            transaction_type="expense",

            category=category,

            payment_method=payment_method,

            transaction_date=transaction_date,

            notes=notes,

            goal=goal,

        )

        goal.current_amount += Decimal(amount)

        if goal.current_amount >= goal.target_amount:

            goal.current_amount = goal.target_amount

            goal.status = "completed"

        goal.save()

        return transaction

    @staticmethod
    @db_transaction.atomic
    def remove_contribution(transaction):

        goal = transaction.goal

        if goal:

            goal.current_amount -= transaction.amount

            if goal.current_amount < 0:

                goal.current_amount = Decimal("0.00")

            if goal.status == "completed":

                goal.status = "active"

            goal.save()

        transaction.delete()

    @staticmethod
    @db_transaction.atomic
    def update_contribution(
        transaction,
        new_amount,
    ):

        goal = transaction.goal

        if goal:

            goal.current_amount -= transaction.amount

            goal.current_amount += Decimal(new_amount)

            if goal.current_amount >= goal.target_amount:

                goal.current_amount = goal.target_amount

                goal.status = "completed"

            else:

                goal.status = "active"

            goal.save()

        transaction.amount = new_amount

        transaction.save()

        return transaction