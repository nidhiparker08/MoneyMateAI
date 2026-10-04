from django.urls import path

from . import views

app_name = "financial_memory"

urlpatterns = [
    path("", views.memory_dashboard, name="dashboard"),
    path("review/", views.review_queue, name="review_queue"),
    path("review/<int:item_id>/resolve/", views.resolve_review, name="resolve_review"),
    path("review/<int:item_id>/dismiss/", views.dismiss_review, name="dismiss_review"),
    path("entries/", views.entries_list, name="entries_list"),
    path("entries/<int:entry_id>/delete/", views.delete_entry, name="delete_entry"),
    path("entries/<int:entry_id>/toggle/", views.toggle_entry, name="toggle_entry"),
    path("detect-recurring/", views.detect_recurring_view, name="detect_recurring"),
    path("api/classify/", views.api_classify, name="api_classify"),
]
