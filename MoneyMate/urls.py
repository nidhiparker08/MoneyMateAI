from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("core.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),

    # Top-level convenience aliases so /profile/ and /settings/ resolve
    # exactly as the navbar / sidebar link to. These reuse the accounts
    # views but bypass the namespaced accounts include to avoid namespace
    # collisions.
    path("profile/", account_views.profile_view, name="profile"),
    path("settings/", account_views.settings_view, name="settings"),

    path("notifications/", include("notifications.urls")),

    path("accounts/", include("allauth.urls")),

    path("gmail/", include("gmail_sync.urls")),
    path("transactions/", include("transactions.urls")),
    path("budgets/", include("budgets.urls")),
    path("reports/", include("reports.urls")),
    path("investments/", include("investments.urls")),
    path("ai/", include("ai.urls")),
    path("goals/", include("goals.urls")),
    path("memory/", include("financial_memory.urls")),
]
