from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from transactions.models import TransactionCategory

from .models import Budget
from .services import BudgetService


@login_required
def budgets_page(request):

    context = BudgetService.get_dashboard_statistics(request.user)

    context["categories"] = (
        TransactionCategory.objects
        .filter(
            user=request.user,
            category_type="expense",
        )
        .order_by("name")
    )

    context["active_page"] = "budgets"

    return render(

        request,

        "budgets/budgets.html",

        context,

    )

@require_POST
@login_required
def create_budget(request):

    try:

        category = get_object_or_404(
            TransactionCategory,
            id=request.POST["category"],
            user=request.user,
        )

        BudgetService.create_budget(

            user=request.user,

            category=category,

            amount=request.POST["amount"],

            month=request.POST["month"],

            year=request.POST["year"],

        )

        return JsonResponse({

            "success": True

        })

    except Exception as e:

        return JsonResponse({

            "success": False,

            "message": str(e)

        })


@require_POST
@login_required
def update_budget(request, budget_id):

    try:

        budget = BudgetService.get_budget(

            request.user,

            budget_id,

        )

        category = get_object_or_404(
            TransactionCategory,
            id=request.POST["category"],
            user=request.user,
        )

        BudgetService.update_budget(

            budget,

            category,

            request.POST["amount"],

            request.POST["month"],

            request.POST["year"],

        )

        return JsonResponse({

            "success": True

        })

    except Exception as e:

        return JsonResponse({

            "success": False,

            "message": str(e)

        })


@require_POST
@login_required
def delete_budget(request, budget_id):

    try:

        budget = BudgetService.get_budget(

            request.user,

            budget_id,

        )

        BudgetService.delete_budget(budget)

        return JsonResponse({

            "success": True

        })

    except Exception as e:

        return JsonResponse({

            "success": False,

            "message": str(e)

        })