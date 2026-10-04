from django.urls import path
from . import views

app_name = "ai"

urlpatterns = [
    path("", views.ai_page, name="ai"),
    path("chat/", views.ai_chat, name="chat"),
    path("clear/", views.ai_clear, name="clear"),
    path("health/", views.ai_health, name="health"),
    path("insights/", views.ai_insights_api, name="insights"),
]
