"""Core response envelope for NexusPay APIs"""
from rest_framework.response import Response
from rest_framework import status
from typing import Any, Optional


class APIResponse:
    """Standardized API response builder"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = status.HTTP_200_OK,
        meta: Optional[dict] = None,
    ) -> Response:
        payload = {
            "success": True,
            "message": message,
            "data": data,
        }
        if meta:
            payload["meta"] = meta
        return Response(payload, status=status_code)

    @staticmethod
    def created(data: Any = None, message: str = "Created successfully") -> Response:
        return APIResponse.success(data=data, message=message, status_code=status.HTTP_201_CREATED)

    @staticmethod
    def error(
        message: str = "An error occurred",
        errors: Any = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: Optional[str] = None,
    ) -> Response:
        payload = {
            "success": False,
            "message": message,
            "errors": errors,
        }
        if error_code:
            payload["error_code"] = error_code
        return Response(payload, status=status_code)

    @staticmethod
    def not_found(message: str = "Resource not found") -> Response:
        return APIResponse.error(message=message, status_code=status.HTTP_404_NOT_FOUND, error_code="NOT_FOUND")

    @staticmethod
    def unauthorized(message: str = "Authentication required") -> Response:
        return APIResponse.error(message=message, status_code=status.HTTP_401_UNAUTHORIZED, error_code="UNAUTHORIZED")

    @staticmethod
    def forbidden(message: str = "Permission denied") -> Response:
        return APIResponse.error(message=message, status_code=status.HTTP_403_FORBIDDEN, error_code="FORBIDDEN")

    @staticmethod
    def validation_error(errors: Any, message: str = "Validation failed") -> Response:
        return APIResponse.error(
            message=message,
            errors=errors,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
        )

    @staticmethod
    def paginated(data: Any, paginator, request, message: str = "Success") -> Response:
        """Helper for paginated responses"""
        page = paginator.paginate_queryset(data, request)
        if page is not None:
            return paginator.get_paginated_response(page)
        return APIResponse.success(data=data, message=message)
