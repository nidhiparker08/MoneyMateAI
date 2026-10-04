from decimal import Decimal

from django.db.models import Sum

from transactions.models import Transaction

from .models import Budget


class BudgetService:

    # =====================================================
    # GET SUMMARY FOR ONE BUDGET
    # =====================================================

    @staticmethod
    def get_budget_summary(budget):

        spent = (

            Transaction.objects.filter(

                user=budget.user,

                category=budget.category,

                transaction_type="expense",

                transaction_date__year=budget.year,

                transaction_date__month=budget.month,

            ).aggregate(

                total=Sum("amount")

            )["total"]

            or Decimal("0.00")

        )

        remaining = budget.amount - spent

        percentage = (

            float(spent / budget.amount * 100)

            if budget.amount > 0

            else 0

        )

        percentage = round(percentage, 1)

        return {

            "budget": budget,

            "spent": spent,

            "remaining": remaining,

            "percentage": percentage,

            "is_exceeded": spent > budget.amount,

        }

    # =====================================================
    # GET ALL SUMMARIES
    # =====================================================

    @staticmethod
    def get_all_budget_summaries(user):

        budgets = (

            Budget.objects

            .filter(user=user)

            .select_related("category")

            .order_by("category__name")

        )

        summaries = [

            BudgetService.get_budget_summary(budget)

            for budget in budgets

        ]

        return summaries

    # =====================================================
    # DASHBOARD TOTALS
    # =====================================================

    @staticmethod
    def get_dashboard_statistics(user):

        summaries = BudgetService.get_all_budget_summaries(user)

        total_budget = sum(

            s["budget"].amount

            for s in summaries

        )

        total_spent = sum(

            s["spent"]

            for s in summaries

        )

        total_remaining = sum(

            s["remaining"]

            for s in summaries

        )

        return {

            "budget_summaries": summaries,

            "total_budget": total_budget,

            "total_spent": total_spent,

            "total_remaining": total_remaining,

            "budget_count": len(summaries),

            "month_choices": Budget.MONTH_CHOICES,

            "years": list(range(2025, 2036)),

        }

        # =====================================================
    # GET SINGLE BUDGET
    # =====================================================

    @staticmethod
    def get_budget(user, budget_id):

        return Budget.objects.get(

            id=budget_id,

            user=user,

        )

    # =====================================================
    # CREATE BUDGET
    # =====================================================

    @staticmethod
    def create_budget(

        user,

        category,

        amount,

        month,

        year,

    ):

        return Budget.objects.create(

            user=user,

            category=category,

            amount=amount,

            month=month,

            year=year,

        )

    # =====================================================
    # UPDATE BUDGET
    # =====================================================

    @staticmethod
    def update_budget(

        budget,

        category,

        amount,

        month,

        year,

    ):

        budget.category = category

        budget.amount = amount

        budget.month = month

        budget.year = year

        budget.save()

        return budget

    # =====================================================
    # DELETE BUDGET
    # =====================================================

    @staticmethod
    def delete_budget(budget):

        budget.delete()