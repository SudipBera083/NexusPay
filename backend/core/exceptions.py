"""Custom exceptions and DRF exception handler for NexusPay"""
import logging
from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger("nexuspay")


# ─── Custom Exceptions ────────────────────────────────────────────────────────

class NexusPayException(Exception):
    """Base exception for NexusPay"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "An error occurred"
    error_code = "NEXUSPAY_ERROR"

    def __init__(self, message: str = None, error_code: str = None):
        self.message = message or self.default_message
        if error_code:
            self.error_code = error_code
        super().__init__(self.message)


class InsufficientBalanceError(NexusPayException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_message = "Insufficient balance"
    error_code = "INSUFFICIENT_BALANCE"


class WalletNotFoundError(NexusPayException):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Wallet not found"
    error_code = "WALLET_NOT_FOUND"


class WalletLockedError(NexusPayException):
    status_code = status.HTTP_423_LOCKED
    default_message = "Wallet is currently locked"
    error_code = "WALLET_LOCKED"


class ExchangeRateUnavailableError(NexusPayException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = "Exchange rate is currently unavailable"
    error_code = "RATE_UNAVAILABLE"


class InvalidCurrencyError(NexusPayException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Invalid currency specified"
    error_code = "INVALID_CURRENCY"


class OTPError(NexusPayException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Invalid or expired OTP"
    error_code = "OTP_ERROR"


class TransactionError(NexusPayException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Transaction failed"
    error_code = "TRANSACTION_ERROR"


class AuthenticationError(NexusPayException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "Authentication failed"
    error_code = "AUTH_ERROR"


class PermissionDeniedError(NexusPayException):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "You do not have permission to perform this action"
    error_code = "PERMISSION_DENIED"


class RateLimitExceededError(NexusPayException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_message = "Rate limit exceeded. Please try again later."
    error_code = "RATE_LIMIT_EXCEEDED"


# ─── Exception Handler ────────────────────────────────────────────────────────

def nexuspay_exception_handler(exc, context):
    """Custom DRF exception handler returning standardized envelope"""

    # Handle our custom exceptions
    if isinstance(exc, NexusPayException):
        logger.warning(
            f"NexusPayException: {exc.error_code} - {exc.message}",
            extra={"view": context.get("view", {})},
        )
        return Response(
            {
                "success": False,
                "message": exc.message,
                "error_code": exc.error_code,
                "errors": None,
            },
            status=exc.status_code,
        )

    # Fall back to DRF default handler
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "success": False,
            "message": _extract_message(response.data),
            "errors": response.data,
            "error_code": _map_status_to_code(response.status_code),
        }
        response.data = error_data

    return response


def _extract_message(data) -> str:
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        first_key = next(iter(data), None)
        if first_key:
            val = data[first_key]
            return str(val[0]) if isinstance(val, list) else str(val)
    if isinstance(data, list) and data:
        return str(data[0])
    return "An error occurred"


def _map_status_to_code(status_code: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status_code, "ERROR")
