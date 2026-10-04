"""Goal-focused insight helpers used by templates/goals/ai_panel.html."""
from datetime import date
from decimal import Decimal
from typing import List, Dict


def _months_to_target(g) -> float:
    """Approximate months required to complete the goal at current pace."""
    from transactions.models import Transaction

    remaining = float(g.target_amount) - float(g.current_amount)
    if remaining <= 0:
        return 0.0
    since = date(2024, 1, 1) if not g.user.date_joined else g.user.date_joined.date()
    # Sum of contributions this year
    contribs = (
        Transaction.objects
        .filter(user=g.user, goal=g, transaction_type="expense")
        .exclude(transaction_date__lt=since)
    )
    months = max(1, (date.today().year - since.year) * 12 + (date.today().month - since.month) + 1)
    total = sum(float(t.amount) for t in contribs)
    monthly_pace = total / months if months else 0.0
    if monthly_pace <= 0:
        return 0.0
    return remaining / monthly_pace


def compute_goal_insights(user) -> Dict:
    """Return real, data-driven insights for /goals/ AI panel."""
    from .models import Goal

    goals = list(Goal.objects.filter(user=user))

    if not goals:
        return {
            "has_goals": False,
            "health_score": 0,
            "closest_goal": None,
            "closest_months": 0,
            "recommend_monthly": 0,
            "behind_count": 0,
            "summary": "Add your first goal (a laptop, a trip, an emergency fund) and MoneyMate will chart the fastest path.",
        }

    active = [g for g in goals if g.status == "active"]

    # Average progress across all goals -> health score (0..100)
    total_target = sum(float(g.target_amount) for g in goals) or 1.0
    total_saved = sum(float(g.current_amount) for g in goals)
    health_score = min(100.0, round(total_saved / total_target * 100, 1))

    # Closest goal by remaining-months
    closest = None
    closest_months = 0.0
    for g in active:
        if float(g.current_amount) >= float(g.target_amount):
            continue
        m = _months_to_target(g)
        if m <= 0:
            continue
        if closest is None or m < closest_months:
            closest = g
            closest_months = m

    # Highest-priority active goal (by priority + deadline)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    priority_goal = sorted(
        active, key=lambda g: (priority_order.get(g.priority, 3), g.deadline)
    )
    top_priority = priority_goal[0] if priority_goal else None

    # Suggested monthly contribution for top priority
    recommend_monthly = 0
    if top_priority:
        remaining = float(top_priority.target_amount) - float(top_priority.current_amount)
        months_left = max(
            1,
            (top_priority.deadline.year - date.today().year) * 12 +
            (top_priority.deadline.month - date.today().month),
        )
        recommend_monthly = int(max(0, remaining / months_left))

    behind = [g for g in active if float(g.progress_percentage or 0) < 25]

    summary_parts = []
    summary_parts.append(
        f"You've saved ₹{total_saved:,.0f} of ₹{total_target:,.0f} across {len(goals)} goal(s)."
    )
    if closest:
        summary_parts.append(
            f"Your closest goal — {closest.title} — is on track to finish in about {int(round(closest_months))} month(s)."
        )
    if top_priority and recommend_monthly:
        summary_parts.append(
            f"Saving roughly ₹{recommend_monthly:,}/month keeps {top_priority.title} on schedule."
        )
    if behind:
        summary_parts.append(
            f"{len(behind)} goal(s) are lagging — a small SIP-style contribution can pull them back."
        )
    summary = " ".join(summary_parts)

    return {
        "has_goals": True,
        "health_score": health_score,
        "closest_goal": closest,
        "closest_months": int(round(closest_months)),
        "recommend_monthly": recommend_monthly,
        "top_priority": top_priority,
        "behind_count": len(behind),
        "summary": summary,
    }
