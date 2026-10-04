from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notifications_page, name="index"),
    path("api/list/", views.api_list, name="api_list"),
    path("api/unread-count/", views.api_unread_count, name="api_unread_count"),
    path("api/mark-read/", views.api_mark_read, name="api_mark_read"),
    path("api/mark-all-read/", views.api_mark_all_read, name="api_mark_all_read"),
    path("api/<int:pk>/dismiss/", views.api_dismiss, name="api_dismiss"),
    path(
        "api/<int:pk>/categorise/",
        views.api_categorise_transaction,
        name="api_categorise",
    ),
    path("api/clear-all/", views.api_clear_all, name="api_clear_all"),
]
