from django.urls import path
from . import views

app_name = "exchange"

urlpatterns = [
    path("rate/", views.CurrentRateView.as_view(), name="current-rate"),
    path("quote/", views.ConversionQuoteView.as_view(), name="quote"),
    path("history/", views.RateHistoryView.as_view(), name="rate-history"),
]
