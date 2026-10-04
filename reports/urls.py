from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [

    path(

        "",

        views.reports_page,

        name="reports",

    ),
    path(

        "download/",

        views.download_report,

        name="download",

    ),

]