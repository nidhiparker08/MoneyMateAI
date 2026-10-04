from decimal import Decimal

from django.db.models import Sum, Count
from django.db.models.functions import Coalesce, TruncMonth

from collections import defaultdict
import json

from transactions.models import Transaction, TransactionCategory
from datetime import date
from datetime import timedelta
from budgets.services import BudgetService


def get_dashboard_summary(user, period="6m"):

    # ==========================================================
    # Categories
    # ==========================================================

    categories = TransactionCategory.objects.filter(
        user=user
    ).order_by("category_type", "name")

    # ==========================================================
    # Transactions
    # ==========================================================

    transactions = (
        Transaction.objects
        .filter(user=user)
        .select_related("category")
    )

    today = date.today()

    if period == "1m":

        start_date = today - timedelta(days=30)

        filtered_transactions = transactions.filter(
            transaction_date__gte=start_date
        )

    elif period == "3m":

        start_date = today - timedelta(days=90)

        filtered_transactions = transactions.filter(
            transaction_date__gte=start_date
        )

    elif period == "6m":

        start_date = today - timedelta(days=180)

        filtered_transactions = transactions.filter(
            transaction_date__gte=start_date
        )

    elif period == "1y":

        start_date = today - timedelta(days=365)

        filtered_transactions = transactions.filter(
            transaction_date__gte=start_date
        )

    else:

        filtered_transactions = transactions

    transactions = filtered_transactions.order_by(
        "-transaction_date",
        "-created_at",
    )

    # ==========================================================
    # Summary
    # ==========================================================

    total_income = (

        Transaction.objects

        .filter(
            user=user,
            transaction_type="income"
        )

        .aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00")
            )
        )["total"]

    )

    total_expense = (

        Transaction.objects

        .filter(
            user=user,
            transaction_type="expense"
        )

        .aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00")
            )
        )["total"]

    )

    total_balance = total_income - total_expense

    transaction_count = transactions.aggregate(
        total=Count("id")
    )["total"]

    # ==========================================================
    # Monthly Summary
    # ==========================================================

    today = date.today()

    this_month = today.month
    this_year = today.year

    if this_month == 1:
        previous_month = 12
        previous_year = this_year - 1
    else:
        previous_month = this_month - 1
        previous_year = this_year


    this_month_income = (
        Transaction.objects
        .filter(
            user=user,
            transaction_type="income",
            transaction_date__month=this_month,
            transaction_date__year=this_year,
        )
        .aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00")
            )
        )["total"]
    )


    previous_month_income = (
        Transaction.objects
        .filter(
            user=user,
            transaction_type="income",
            transaction_date__month=previous_month,
            transaction_date__year=previous_year,
        )
        .aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00")
            )
        )["total"]
    )


    this_month_expense = (
        Transaction.objects
        .filter(
            user=user,
            transaction_type="expense",
            transaction_date__month=this_month,
            transaction_date__year=this_year,
        )
        .aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00")
            )
        )["total"]
    )


    previous_month_expense = (
        Transaction.objects
        .filter(
            user=user,
            transaction_type="expense",
            transaction_date__month=previous_month,
            transaction_date__year=previous_year,
        )
        .aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00")
            )
        )["total"]
    )

    # ==========================================================
    # Budget
    # ==========================================================

    budget_data = BudgetService.get_dashboard_statistics(user)

    budget_used = budget_data["total_spent"]

    budget_remaining = budget_data["total_remaining"]

    total_budget = budget_data["total_budget"]

    budget_count = budget_data["budget_count"]

    budget_percentage = 0

    if total_budget > 0:

        budget_percentage = round(

            float(budget_used / total_budget) * 100,

            1,

        )

        budget_percentage = min(budget_percentage, 100)

    # ==========================================================
    # Recent Transactions
    # ==========================================================

    recent_transactions = transactions[:5]

    # ==========================================================
    # Dashboard State
    # ==========================================================

    has_transactions = transaction_count > 0

    # ==========================================================
    # Expense Trend (Last 6 Months)
    # ==========================================================

    expense_trend = (

        filtered_transactions

        .filter(
            transaction_type="expense"
        )

        .annotate(
            month=TruncMonth("transaction_date")
        )

        .values("month")

        .annotate(
            total=Sum("amount")
        )

        .order_by("month")

    )

    expense_trend_json = [

        {

            "label": item["month"].strftime("%b %Y"),

            "value": float(item["total"])

        }

        for item in expense_trend

    ]

    # ==========================================================
    # Category Breakdown
    # ==========================================================

    category_data = (

        filtered_transactions

        .filter(
            transaction_type="expense"
        )

        .values("category__name")

        .annotate(
            total=Sum("amount")
        )

        .order_by("-total")

    )

    category_breakdown_json = {

        "labels": [

            row["category__name"] or "Other"

            for row in category_data

        ],

        "values": [

            float(row["total"])

            for row in category_data

        ]

    }

    # ==========================================================
    # Cash Flow (Income vs Expense)
    # ==========================================================

    monthly = defaultdict(

        lambda: {

            "income": 0,

            "expense": 0

        }

    )

    cash_rows = (

        filtered_transactions

        .filter(

            transaction_type__in=["income", "expense"]

        )

        .annotate(
            month=TruncMonth("transaction_date")
        )

        .values(
            "month",
            "transaction_type"
        )

        .annotate(
            total=Sum("amount")
        )

        .order_by("month")

    )

    for row in cash_rows:

        label = row["month"].strftime("%b %Y")

        monthly[label][row["transaction_type"]] = float(

            row["total"]

        )

    cash_flow_json = {

        "labels": list(monthly.keys()),

        "income": [

            monthly[m]["income"]

            for m in monthly

        ],

        "expense": [

            monthly[m]["expense"]

            for m in monthly

        ]

    }

    expense_trend_json = json.dumps(expense_trend_json)

    cash_flow_json = json.dumps(cash_flow_json)

    category_breakdown_json = json.dumps(category_breakdown_json)

    # ==========================================================
    # ==========================================================
    # AI  (real, data-driven — powered by ai.insight_engine)
    # ==========================================================

    ai = {
        "has_insights": False,
        "health_score": 0,
        "saved_30d": 0,
        "message": "",
        "top_insights": [],
    }

    try:
        if has_transactions:
            from ai.insight_engine import generate_insights_v2, narrate_summary
            from ai.services import compute_health_score
            from datetime import timedelta as _td

            insights = generate_insights_v2(user, limit=4)
            health = compute_health_score(user)

            _last_30 = today - _td(days=30)
            _tx_30 = Transaction.objects.filter(user=user, transaction_date__gte=_last_30)
            _inc = _tx_30.filter(transaction_type="income").aggregate(
                s=Coalesce(Sum("amount"), Decimal("0.00"))
            )["s"]
            _exp = _tx_30.filter(transaction_type="expense").aggregate(
                s=Coalesce(Sum("amount"), Decimal("0.00"))
            )["s"]

            ai = {
                "has_insights": True,
                "health_score": health.get("score", 0),
                "saved_30d": float(_inc - _exp),
                "message": narrate_summary(user, insights),
                "top_insights": insights[:3],
            }
    except Exception:
        pass

    # ==========================================================
    # Financial Memory (learning stats)
    # ==========================================================

    memory_stats = {
        "total_memories": 0,
        "aliases": 0,
        "recurring": 0,
        "pending_reviews": 0,
        "total_hits": 0,
    }
    try:
        from financial_memory.services import memory_service
        memory_stats = memory_service.stats_for_user(user)
    except Exception:
        pass

    return {

        "categories": categories,

        "transactions": transactions,

        "recent_transactions": recent_transactions,

        "total_income": total_income,

        "total_expense": total_expense,

        "total_balance": total_balance,

        "net_savings": total_balance,

        "this_month_income": this_month_income,

        "previous_month_income": previous_month_income,

        "this_month_expense": this_month_expense,

        "previous_month_expense": previous_month_expense,

        "transaction_count": transaction_count,

        "budget_used": budget_used,

        "budget_remaining": budget_remaining,

        "budget_percentage": budget_percentage,

        "has_transactions": has_transactions,

        "expense_trend_json": expense_trend_json,

        "cash_flow_json": cash_flow_json,

        "category_breakdown_json": category_breakdown_json,

        "total_budget": total_budget,

        "budget_count": budget_count,

        "selected_period": period,

        "ai": ai,

        "memory_stats": memory_stats,

    }