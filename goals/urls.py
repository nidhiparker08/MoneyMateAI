from django.urls import path

from . import views

app_name = "goals"

urlpatterns = [

    # ==========================================
    # Goals Dashboard
    # ==========================================

    path(
        "",
        views.goal_list,
        name="goal_list",
    ),

    # ==========================================
    # CRUD
    # ==========================================

    path(
        "add/",
        views.add_goal,
        name="add_goal",
    ),

    path(
        "<int:pk>/edit/",
        views.edit_goal,
        name="edit_goal",
    ),

    path(
        "<int:pk>/delete/",
        views.delete_goal,
        name="delete_goal",
    ),

    # ==========================================
    # Contributions
    # ==========================================

    path(
        "<int:goal_id>/contribute/",
        views.contribute_to_goal,
        name="contribute_goal",
    ),

]