from django.urls import path
from . import views

app_name = "transactions"

urlpatterns = [
    path("convert/", views.ConvertView.as_view(), name="convert"),
    path("conversions/", views.ConversionHistoryListView.as_view(), name="conversions"),
    path("pay/", views.PaymentView.as_view(), name="pay"),
    path("payments/", views.PaymentHistoryListView.as_view(), name="payments"),
]
