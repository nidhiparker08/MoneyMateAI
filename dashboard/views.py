from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from transactions.forms import TransactionForm
from .services import get_dashboard_summary


@login_required(login_url="accounts:login")
def dashboard(request):

    period = request.GET.get("period", "6m")

    context = get_dashboard_summary(

        request.user,

        period,

    )

    context["transaction_form"] = TransactionForm(user=request.user)

    context["selected_period"] = period
    context["active_page"] = "dashboard"

    context["selected_period_text"] = {

        "1m": "Last Month",

        "3m": "Last 3 Months",

        "6m": "Last 6 Months",

        "1y": "Last Year",

        "all": "All Time",

    }.get(period, "Last 6 Months")

    return render(

        request,

        "dashboard/dashboard.html",

        context,

    )