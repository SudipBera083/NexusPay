from django.urls import path
from . import views

app_name = "merchants"

urlpatterns = [
    path("register/", views.MerchantRegistrationView.as_view(), name="register"),
    path("profile/", views.MerchantProfileView.as_view(), name="profile"),
    path("analytics/", views.MerchantAnalyticsView.as_view(), name="analytics"),
    path("qr/", views.MerchantQRListView.as_view(), name="qr-list"),
    path("qr/generate/", views.GenerateQRView.as_view(), name="qr-generate"),
    path("qr/<str:nonce>/", views.QRStatusView.as_view(), name="qr-status"),
    path("qr/scan/", views.ScanQRView.as_view(), name="qr-scan"),
    path("qr/submit-tx/", views.SubmitQRTransactionView.as_view(), name="qr-submit-tx"),
]
