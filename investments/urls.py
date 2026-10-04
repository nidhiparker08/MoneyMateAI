from django.urls import path
from . import views

app_name = "investments"

urlpatterns = [
    path("", views.investments_page, name="investments"),
    path("holdings/add/", views.add_holding, name="add_holding"),
    path("holdings/<int:pk>/delete/", views.delete_holding, name="delete_holding"),
    path("suggestions/generate/", views.generate_suggestions, name="generate_suggestions"),
    path("prices/refresh/", views.refresh_prices, name="refresh_prices"),
    path("quote/", views.quote, name="quote"),
]
