from django.urls import path
from . import views

app_name = "wallet"

urlpatterns = [
    path("", views.WalletDetailView.as_view(), name="detail"),
    path("deposit/", views.DepositView.as_view(), name="deposit"),
    path("transactions/", views.WalletTransactionListView.as_view(), name="transactions"),
    path("transactions/<uuid:tx_id>/", views.WalletTransactionDetailView.as_view(), name="transaction-detail"),
    path("web3/link/", views.Web3ConnectView.as_view(), name="web3-link"),
]
