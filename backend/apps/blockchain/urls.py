from django.urls import path
from . import views

app_name = "blockchain"

urlpatterns = [
    path("transactions/", views.BlockchainTransactionListView.as_view(), name="tx-list"),
    path("transactions/<str:tx_hash>/", views.BlockchainTransactionDetailView.as_view(), name="tx-detail"),
    path("submit/", views.SubmitBlockchainTransactionView.as_view(), name="submit"),
    path("settlements/", views.UserSettlementsView.as_view(), name="settlements"),
    path("health/", views.BlockchainHealthView.as_view(), name="health"),
]
