"""Health check endpoints"""
from django.urls import path
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


def health_check(request):
    """Basic health check"""
    return JsonResponse({"status": "ok", "service": "NexusPay API"})


def health_detail(request):
    """Detailed health check with DB and cache status"""
    status = {"status": "ok", "checks": {}}
    try:
        connection.ensure_connection()
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {e}"
        status["status"] = "degraded"

    try:
        cache.set("health_check", "ok", 5)
        val = cache.get("health_check")
        status["checks"]["cache"] = "ok" if val == "ok" else "error"
    except Exception as e:
        status["checks"]["cache"] = f"error: {e}"
        status["status"] = "degraded"

    return JsonResponse(status)


urlpatterns = [
    path("", health_check),
    path("detail/", health_detail),
]
