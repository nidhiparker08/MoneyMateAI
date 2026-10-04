"""Financial context builder for AI assistant."""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum


def build_user_context(user) -> str:
    """Compress the user's finances into a concise text block for the LLM."""
    from transactions.models import Transaction
    from goals.models import Goal
    try:
        from investments.models import Holding
        from investments.services import portfolio_summary
    except Exception:
        Holding = None
        portfolio_summary = None

    today = date.today()
    month_start = today.replace(day=1)
    last_30 = today - timedelta(days=30)

    tx_30 = Transaction.objects.filter(user=user, transaction_date__gte=last_30)
    income = tx_30.filter(transaction_type="income").aggregate(s=Sum("amount"))["s"] or Decimal("0")
    expense = tx_30.filter(transaction_type="expense").aggregate(s=Sum("amount"))["s"] or Decimal("0")

    # Top categories
    by_cat = (
        tx_30.filter(transaction_type="expense")
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:5]
    )
    cat_lines = [
        f"  - {row['category__name'] or 'Uncategorised'}: ₹{row['total']:.0f}"
        for row in by_cat
    ]

    goals = Goal.objects.filter(user=user, status="active")[:5]
    goal_lines = [
        f"  - {g.title}: ₹{g.current_amount:.0f} / ₹{g.target_amount:.0f} "
        f"({g.progress_percentage}%), deadline {g.deadline}"
        for g in goals
    ]

    inv_line = ""
    if Holding and portfolio_summary:
        try:
            s = portfolio_summary(user)
            if s["holding_count"]:
                inv_line = (
                    f"Investments: {s['holding_count']} holdings, invested ₹{s['invested']:.0f}, "
                    f"current ₹{s['current']:.0f}, P&L ₹{s['pnl']:.0f} ({s['pnl_percent']}%).\n"
                )
        except Exception:
            pass

    # Include what the Financial Memory Engine has learned about this user
    # (recurring subscriptions, salary source, investment platforms, etc.)
    memory_block = ""
    try:
        from financial_memory.services import memory_service
        memory_block = memory_service.summary_context(user)
    except Exception:
        pass

    context = (
        f"USER FINANCIAL SNAPSHOT (last 30 days)\n"
        f"Income: ₹{income:.0f} | Expenses: ₹{expense:.0f} | Net: ₹{(income - expense):.0f}\n"
        f"Top expense categories:\n" + ("\n".join(cat_lines) if cat_lines else "  (none)") + "\n"
        f"Active goals:\n" + ("\n".join(goal_lines) if goal_lines else "  (none)") + "\n"
        f"{inv_line}"
        + (f"\nFINANCIAL MEMORY (learned patterns)\n{memory_block}\n" if memory_block else "")
        + f"Currency: INR. Location: India."
    )
    return context


def build_system_message(user) -> str:
    return (
        "You are MoneyMate, a friendly personal finance coach for Indian users. "
        "Give practical, concise, numbers-backed guidance in INR. "
        "Keep replies short (max 6 short paragraphs or bullets) and actionable. "
        "You may reference the user's snapshot below. Do not invent numbers not shown.\n\n"
        + build_user_context(user)
        + "\n\nNever provide guaranteed investment returns. Add 'This is educational, not financial advice.' at the end when giving investment guidance."
    )


def generate_insights(user) -> list[dict]:
    """Return quick financial insights (rule-based, always fast)."""
    from transactions.models import Transaction
    from goals.models import Goal
    from datetime import date, timedelta
    today = date.today()
    last_30 = today - timedelta(days=30)
    prev_30 = last_30 - timedelta(days=30)

    tx_recent = Transaction.objects.filter(user=user, transaction_date__gte=last_30)
    tx_prev = Transaction.objects.filter(
        user=user, transaction_date__gte=prev_30, transaction_date__lt=last_30
    )

    income = tx_recent.filter(transaction_type="income").aggregate(s=Sum("amount"))["s"] or Decimal("0")
    expense = tx_recent.filter(transaction_type="expense").aggregate(s=Sum("amount"))["s"] or Decimal("0")
    prev_expense = tx_prev.filter(transaction_type="expense").aggregate(s=Sum("amount"))["s"] or Decimal("0")

    insights = []

    # Savings rate
    if income > 0:
        savings_rate = float((income - expense) / income * 100)
        if savings_rate >= 30:
            insights.append({
                "icon": "fa-piggy-bank", "tone": "positive",
                "title": "Great savings rate!",
                "body": f"You're saving {savings_rate:.0f}% of income this month — well above the 20% benchmark.",
            })
        elif savings_rate >= 10:
            insights.append({
                "icon": "fa-piggy-bank", "tone": "warn",
                "title": "Savings could improve",
                "body": f"Current savings rate is {savings_rate:.0f}%. Aim for 20%+ by trimming top expense categories.",
            })
        else:
            insights.append({
                "icon": "fa-triangle-exclamation", "tone": "danger",
                "title": "Spending exceeds healthy limits",
                "body": f"Savings rate is only {savings_rate:.0f}%. Consider a monthly budget cap on your top expense.",
            })

    # Month-over-month
    if prev_expense > 0:
        change = float((expense - prev_expense) / prev_expense * 100)
        if change > 15:
            insights.append({
                "icon": "fa-arrow-trend-up", "tone": "warn",
                "title": "Expenses up sharply",
                "body": f"Spending is up {change:.0f}% versus the previous 30 days.",
            })
        elif change < -10:
            insights.append({
                "icon": "fa-arrow-trend-down", "tone": "positive",
                "title": "Nice — expenses down",
                "body": f"Spending is down {abs(change):.0f}% versus the previous 30 days.",
            })

    # Top category
    top_cat = (
        tx_recent.filter(transaction_type="expense")
        .values("category__name").annotate(total=Sum("amount"))
        .order_by("-total").first()
    )
    if top_cat and top_cat["total"] and expense > 0:
        share = float(top_cat["total"] / expense * 100)
        if share > 40:
            insights.append({
                "icon": "fa-chart-pie", "tone": "warn",
                "title": f"Heavy on {top_cat['category__name'] or 'one category'}",
                "body": f"{share:.0f}% of expenses go to {top_cat['category__name'] or 'one category'}. Diversify to reduce risk.",
            })

    # Goals
    active_goals = Goal.objects.filter(user=user, status="active")
    behind = [g for g in active_goals if g.progress_percentage < 25]
    if behind:
        insights.append({
            "icon": "fa-bullseye", "tone": "warn",
            "title": f"{len(behind)} goal(s) behind schedule",
            "body": "Consider setting up a monthly SIP-style contribution to catch up.",
        })

    if not insights:
        insights.append({
            "icon": "fa-lightbulb", "tone": "info",
            "title": "Log a few transactions",
            "body": "Add transactions and goals so I can generate personalised insights.",
        })

    return insights


def compute_health_score(user) -> dict:
    """Simple, transparent 0-100 financial-health score."""
    from transactions.models import Transaction
    from goals.models import Goal
    from datetime import date, timedelta

    today = date.today()
    last_30 = today - timedelta(days=30)
    tx = Transaction.objects.filter(user=user, transaction_date__gte=last_30)
    income = float(tx.filter(transaction_type="income").aggregate(s=Sum("amount"))["s"] or 0)
    expense = float(tx.filter(transaction_type="expense").aggregate(s=Sum("amount"))["s"] or 0)

    # Savings rate score (0-50)
    if income > 0:
        sr = max(0.0, min(1.0, (income - expense) / income / 0.3))  # 30% -> full
        savings_score = sr * 50
    else:
        savings_score = 0

    # Goal progress (0-25)
    goals = list(Goal.objects.filter(user=user))
    if goals:
        avg_progress = sum(float(g.progress_percentage or 0) for g in goals) / len(goals)
        goal_score = min(25.0, avg_progress / 100 * 25)
    else:
        goal_score = 5  # small floor

    # Consistency (0-25) — tx activity in last 30d
    days_active = tx.values("transaction_date").distinct().count()
    consistency_score = min(25.0, days_active / 15 * 25)

    total = round(savings_score + goal_score + consistency_score, 1)
    if total >= 80:
        rating = "Excellent"
    elif total >= 60:
        rating = "Good"
    elif total >= 40:
        rating = "Fair"
    else:
        rating = "Needs work"

    return {
        "score": total,
        "rating": rating,
        "breakdown": {
            "savings": round(savings_score, 1),
            "goals": round(goal_score, 1),
            "consistency": round(consistency_score, 1),
        },
    }
