from django.urls import path

from . import views

app_name = "budgets"

urlpatterns = [

    path(

        "",

        views.budgets_page,

        name="budgets",

    ),

    path(

        "create/",

        views.create_budget,

        name="create",

    ),

    path(

        "update/<int:budget_id>/",

        views.update_budget,

        name="update",

    ),

    path(

        "delete/<int:budget_id>/",

        views.delete_budget,

        name="delete",

    ),

]