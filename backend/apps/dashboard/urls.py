from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("overview/", views.DashboardOverviewView.as_view(), name="overview"),
    path("analytics/", views.SpendingAnalyticsView.as_view(), name="analytics"),
]
