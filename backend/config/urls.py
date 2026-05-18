"""NexusPay URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # API v1
    path("api/v1/auth/", include("apps.authentication.urls", namespace="auth")),
    path("api/v1/wallet/", include("apps.wallet.urls", namespace="wallet")),
    path("api/v1/exchange/", include("apps.exchange.urls", namespace="exchange")),
    path("api/v1/transactions/", include("apps.transactions.urls", namespace="transactions")),
    path("api/v1/dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("api/v1/admin-panel/", include("apps.admin_panel.urls", namespace="admin_panel")),
    path("api/v1/blockchain/", include("apps.blockchain.urls", namespace="blockchain")),
    path("api/v1/merchants/", include("apps.merchants.urls", namespace="merchants")),

    # API Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Health check
    path("health/", include("apps.dashboard.health_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
