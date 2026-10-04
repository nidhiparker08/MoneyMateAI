from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import GoalForm
from .models import Goal

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .services import GoalContributionService
from .forms import GoalContributionForm


@login_required
def goal_list(request):
    """
    Display all goals and provide an empty form
    for the Add Goal modal.
    """
    from .insights import compute_goal_insights

    goals = Goal.objects.filter(user=request.user).order_by("deadline")

    context = {
        "goals": goals,
        "form": GoalForm(),

        "contribution_form": GoalContributionForm(
            user=request.user
        ),

        "goal_count": goals.count(),

        "total_target": sum(goal.target_amount for goal in goals),

        "total_saved": sum(goal.current_amount for goal in goals),

        "completed": goals.filter(status="completed").count(),

        "goal_ai": compute_goal_insights(request.user),

        "active_page": "goals",
    }

    return render(
        request,
        "goals/goals.html",
        context
    )


@login_required
def add_goal(request):
    """
    Create a new goal.
    """

    if request.method != "POST":
        return redirect("goals:goal_list")

    form = GoalForm(request.POST)

    if form.is_valid():

        goal = form.save(commit=False)

        goal.user = request.user

        goal.save()

        messages.success(
            request,
            "Goal created successfully!"
        )

    else:

        messages.error(
            request,
            "Please correct the errors in the form."
        )

    return redirect("goals:goal_list")


@login_required
def edit_goal(request, pk):
    """
    Edit an existing goal.
    """

    goal = get_object_or_404(
        Goal,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":

        form = GoalForm(
            request.POST,
            instance=goal
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Goal updated successfully!"
            )

            return redirect("goals:goal_list")

    else:

        form = GoalForm(instance=goal)

    return render(
        request,
        "goals/edit_goal.html",
        {
            "form": form,
            "goal": goal,
        }
    )


@login_required
def delete_goal(request, pk):
    """
    Delete a goal.
    """

    goal = get_object_or_404(
        Goal,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":

        goal.delete()

        messages.success(
            request,
            "Goal deleted successfully!"
        )

    return redirect("goals:goal_list")

# ==========================================================
# GOAL CONTRIBUTION
# ==========================================================

@login_required
@require_POST
def contribute_to_goal(request, goal_id):

    form = GoalContributionForm(

        request.POST,

        user=request.user,

    )

    if not form.is_valid():

        return JsonResponse(

            {

                "success": False,

                "errors": form.errors,

            },

            status=400,

        )

    try:

        transaction = GoalContributionService.add_contribution(

            user=request.user,

            goal_id=goal_id,

            amount=form.cleaned_data["amount"],

            transaction_date=form.cleaned_data["transaction_date"],

            payment_method=form.cleaned_data["payment_method"],

            category=form.cleaned_data["category"],

            notes=form.cleaned_data["notes"],

            title="Goal Contribution",

        )

        return JsonResponse(

            {

                "success": True,

                "message": "Contribution added successfully.",

                "transaction_id": transaction.id,

            }

        )

    except Exception as e:

        return JsonResponse(

            {

                "success": False,

                "message": str(e),

            },

            status=400,

        )