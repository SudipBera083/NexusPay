"""Custom middleware for NexusPay"""
import logging
import time
import uuid
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("nexuspay")


class RequestLoggingMiddleware(MiddlewareMixin):
    """Logs every incoming request with timing, method, path, status"""

    def process_request(self, request):
        request._start_time = time.time()
        request._request_id = str(uuid.uuid4())[:8]
        request.META["HTTP_X_REQUEST_ID"] = request._request_id

    def process_response(self, request, response):
        duration_ms = int((time.time() - getattr(request, "_start_time", time.time())) * 1000)
        req_id = getattr(request, "_request_id", "-")
        user = getattr(request, "user", None)
        user_info = f"user={user.id}" if user and user.is_authenticated else "anonymous"

        logger.info(
            f"[{req_id}] {request.method} {request.path} "
            f"→ {response.status_code} ({duration_ms}ms) [{user_info}]"
        )

        response["X-Request-ID"] = req_id
        response["X-Response-Time"] = f"{duration_ms}ms"
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Adds security headers to every response"""

    def process_response(self, request, response):
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        return response
