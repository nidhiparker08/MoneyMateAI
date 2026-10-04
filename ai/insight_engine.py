"""Rich, LLM-narrated AI insights for the whole app.

`generate_insights_v2(user)` returns a list of dict insights that are always
derived from the user's real data (transactions, goals, budgets, memory).
Numbers are rule-based (fast, deterministic); the narrative body is
optionally enhanced by Gemini when GEMINI_API_KEY is present. If Gemini
is unavailable, the rule-based fallback still produces meaningful copy.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict

from django.db.models import Sum


@dataclass
class Insight:
    icon: str
    tone: str  # positive | warn | danger | info
    title: str
    body: str
    action_url: str = ""
    action_label: str = ""

    def to_dict(self) -> Dict:
        return {
            "icon": self.icon,
            "tone": self.tone,
            "title": self.title,
            "body": self.body,
            "action_url": self.action_url,
            "action_label": self.action_label,
        }


def _f(v):  # safe float
    try:
        return float(v)
    except Exception:
        return 0.0


def _totals(qs):
    inc = _f(qs.filter(transaction_type="income").aggregate(s=Sum("amount"))["s"] or 0)
    exp = _f(qs.filter(transaction_type="expense").aggregate(s=Sum("amount"))["s"] or 0)
    return inc, exp


def _top_category(qs):
    row = (
        qs.filter(transaction_type="expense")
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
        .first()
    )
    if not row or not row["total"]:
        return None, 0.0
    return row["category__name"] or "Uncategorised", _f(row["total"])


def generate_insights_v2(user, limit: int = 6) -> List[Dict]:
    from transactions.models import Transaction
    from goals.models import Goal

    today = date.today()
    last_30 = today - timedelta(days=30)
    prev_30 = last_30 - timedelta(days=30)

    tx_recent = Transaction.objects.filter(user=user, transaction_date__gte=last_30)
    tx_prev = Transaction.objects.filter(
        user=user,
        transaction_date__gte=prev_30,
        transaction_date__lt=last_30,
    )
    tx_lifetime = Transaction.objects.filter(user=user)

    income_30, expense_30 = _totals(tx_recent)
    _, expense_prev = _totals(tx_prev)
    lifetime_income, lifetime_expense = _totals(tx_lifetime)

    insights: List[Insight] = []

    # ---------- Highest spending category ----------
    top_name, top_amt = _top_category(tx_recent)
    if top_name and expense_30 > 0:
        share = (top_amt / expense_30) * 100 if expense_30 else 0
        tone = "warn" if share > 40 else "info"
        insights.append(Insight(
            icon="fa-chart-pie", tone=tone,
            title=f"Top category: {top_name}",
            body=(
                f"₹{top_amt:,.0f} ({share:.0f}% of last-30-day spend) went to {top_name}. "
                + ("Try trimming this to lift your savings rate." if share > 40 else "Balanced allocation so far.")
            ),
            action_url="/transactions/",
            action_label="View transactions",
        ))

    # ---------- Month-over-month trend ----------
    if expense_prev > 0:
        change = (expense_30 - expense_prev) / expense_prev * 100
        if change > 15:
            insights.append(Insight(
                icon="fa-arrow-trend-up", tone="warn",
                title="Spending up sharply",
                body=f"Expenses are up {change:.0f}% vs the previous 30 days (₹{expense_30:,.0f} vs ₹{expense_prev:,.0f}).",
            ))
        elif change < -10:
            insights.append(Insight(
                icon="fa-arrow-trend-down", tone="positive",
                title="Nice — expenses trending down",
                body=f"Spending is down {abs(change):.0f}% vs the previous 30 days. Keep the momentum going.",
            ))

    # ---------- Savings rate ----------
    if income_30 > 0:
        savings_rate = (income_30 - expense_30) / income_30 * 100
        if savings_rate >= 30:
            insights.append(Insight(
                icon="fa-piggy-bank", tone="positive",
                title="Excellent savings rate",
                body=f"You saved {savings_rate:.0f}% of last month's income — well above the 20% benchmark.",
            ))
        elif savings_rate >= 10:
            insights.append(Insight(
                icon="fa-piggy-bank", tone="warn",
                title="Room to save more",
                body=f"You're saving {savings_rate:.0f}% of income. Aim for 20%+ by trimming the top category.",
            ))
        else:
            insights.append(Insight(
                icon="fa-triangle-exclamation", tone="danger",
                title="Savings rate is thin",
                body=f"Only {savings_rate:.0f}% is being saved. Consider a cap on discretionary spend.",
                action_url="/budgets/",
                action_label="Set a budget",
            ))

    # ---------- Spending streak (# active days last 30) ----------
    days_active = tx_recent.values("transaction_date").distinct().count()
    if days_active >= 20:
        insights.append(Insight(
            icon="fa-fire", tone="positive",
            title=f"{days_active}-day tracking streak",
            body="You're logging transactions consistently — the AI can learn your habits better every week.",
        ))

    # ---------- Recurring / subscription detection via financial_memory ----------
    try:
        from financial_memory.services import memory_service
        stats = memory_service.stats_for_user(user)
        rec = int(stats.get("recurring", 0))
        pending = int(stats.get("pending_reviews", 0))
        if rec:
            insights.append(Insight(
                icon="fa-repeat", tone="info",
                title=f"{rec} recurring pattern{'s' if rec != 1 else ''}",
                body="MoneyMate spotted repeated payments (rent, subscriptions, EMIs). Review them to hunt for hidden spend.",
                action_url="/memory/", action_label="Open memory",
            ))
        if pending:
            insights.append(Insight(
                icon="fa-inbox", tone="warn",
                title=f"{pending} transaction{'s' if pending != 1 else ''} need review",
                body="Correct the categories so the AI remembers them forever.",
                action_url="/memory/review/", action_label="Review now",
            ))
    except Exception:
        pass

    # ---------- Budget warnings ----------
    try:
        from budgets.services import BudgetService
        b = BudgetService.get_dashboard_statistics(user)
        total_budget = _f(b.get("total_budget", 0))
        total_spent = _f(b.get("total_spent", 0))
        if total_budget > 0:
            used_pct = total_spent / total_budget * 100
            if used_pct >= 100:
                insights.append(Insight(
                    icon="fa-triangle-exclamation", tone="danger",
                    title="Monthly budget exceeded",
                    body=f"You've spent ₹{total_spent:,.0f} of a ₹{total_budget:,.0f} budget ({used_pct:.0f}%).",
                    action_url="/budgets/", action_label="Review budgets",
                ))
            elif used_pct >= 80:
                insights.append(Insight(
                    icon="fa-gauge-high", tone="warn",
                    title="Budget nearly used up",
                    body=f"{used_pct:.0f}% of your monthly budget is spent — pace yourself for the rest of the month.",
                    action_url="/budgets/", action_label="View budgets",
                ))
    except Exception:
        pass

    # ---------- Goals: behind schedule ----------
    active_goals = list(Goal.objects.filter(user=user, status="active"))
    behind = [g for g in active_goals if _f(g.progress_percentage) < 25]
    if behind:
        insights.append(Insight(
            icon="fa-bullseye", tone="warn",
            title=f"{len(behind)} goal{'s' if len(behind) != 1 else ''} behind schedule",
            body="Set up a small monthly SIP-style contribution to catch up before your deadline.",
            action_url="/goals/", action_label="Open goals",
        ))

    # ---------- Fallback ----------
    if not insights:
        insights.append(Insight(
            icon="fa-lightbulb", tone="info",
            title="Log a few transactions",
            body="Add income & expenses so MoneyMate can turn your data into insights.",
            action_url="/transactions/", action_label="Add transaction",
        ))

    return [i.to_dict() for i in insights[:limit]]


def narrate_summary(user, insights: List[Dict]) -> str:
    """Optional Gemini-narrated one-paragraph coach summary.
    Falls back to a rule-based sentence when the LLM isn't reachable."""
    numbers = "; ".join(f"{i['title']}: {i['body']}" for i in insights[:4])
    fallback = (
        "Based on your latest 30-day activity, focus on the top-spending category "
        "and lift your savings rate toward 20%+. Small, consistent trims compound quickly."
    )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return fallback
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        prompt = (
            "You are MoneyMate, a warm personal-finance coach for an Indian user. "
            "Write ONE short paragraph (max 3 sentences, no more than 55 words) that "
            "synthesises these observations into a practical, encouraging summary "
            "in INR. Do not repeat the numbers verbatim — paraphrase. Do not add "
            "disclaimers, headings, or lists.\n\n"
            f"Observations:\n{numbers}"
        )
        resp = client.models.generate_content(model=model, contents=prompt)
        text = (getattr(resp, "text", "") or "").strip()
        return text or fallback
    except Exception:
        return fallback
