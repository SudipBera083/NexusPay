from django.urls import path
from . import views

app_name = "admin_panel"

urlpatterns = [
    path("stats/", views.AdminStatsView.as_view(), name="stats"),
    path("users/", views.AdminUserListView.as_view(), name="users"),
    path("users/<uuid:user_id>/", views.AdminUserDetailView.as_view(), name="user-detail"),
    path("users/<uuid:user_id>/wallet/", views.AdminWalletInspectView.as_view(), name="wallet-inspect"),
    path("transactions/", views.AdminTransactionMonitorView.as_view(), name="transactions"),
    path("transactions/<uuid:tx_id>/reverse/", views.AdminReverseTransactionView.as_view(), name="reverse"),
    path("audit-logs/", views.AdminAuditLogView.as_view(), name="audit-logs"),
    path("exchange-rate/override/", views.AdminSetExchangeRateView.as_view(), name="rate-override"),
]
