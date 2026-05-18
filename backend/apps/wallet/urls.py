from django.urls import path
from . import views

app_name = "wallet"

urlpatterns = [
    path("", views.WalletDetailView.as_view(), name="detail"),
    # Legacy simulate deposit kept for dev/admin use
    path("deposit/", views.DepositView.as_view(), name="deposit"),
    # Real UPI / card on-ramp via Razorpay
    path("deposit/upi/initiate/", views.RazorpayInitiateView.as_view(), name="upi-initiate"),
    path("deposit/upi/webhook/", views.RazorpayWebhookView.as_view(), name="upi-webhook"),
    path("withdraw/", views.WithdrawView.as_view(), name="withdraw"),
    path("transactions/", views.WalletTransactionListView.as_view(), name="transactions"),
    path("transactions/<uuid:tx_id>/", views.WalletTransactionDetailView.as_view(), name="transaction-detail"),
    path("web3/link/", views.Web3ConnectView.as_view(), name="web3-link"),
]

