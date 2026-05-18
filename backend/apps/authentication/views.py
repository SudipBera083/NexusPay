"""Authentication views for NexusPay"""
import logging
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.response import APIResponse
from core.exceptions import AuthenticationError, OTPError
from .models import User
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    NexusPayTokenObtainPairSerializer,
)
from .tasks import send_otp_task

logger = logging.getLogger("nexuspay")


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Authentication"],
        request=RegisterSerializer,
        summary="Register a new user",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        user = serializer.save()

        # Create wallet for new user
        from apps.wallet.services import WalletService
        WalletService.create_wallet(user)

        # Generate and send OTP
        otp_code = user.generate_otp()
        if settings.OTP_SIMULATION_MODE:
            logger.info(f"[OTP SIMULATION] User {user.email} OTP: {otp_code}")
        else:
            send_otp_task.delay(user.email, otp_code)

        tokens = RefreshToken.for_user(user)
        data = {
            "user": UserProfileSerializer(user).data,
            "tokens": {
                "access": str(tokens.access_token),
                "refresh": str(tokens),
            },
            "otp_sent": True,
            "otp_simulation": settings.OTP_SIMULATION_MODE,
            **({"otp_code": otp_code} if settings.OTP_SIMULATION_MODE else {}),
        }
        return APIResponse.created(data=data, message="Account created successfully. Please verify your OTP.")


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(tags=["Authentication"], request=LoginSerializer, summary="Login with email/password")
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        user = serializer.validated_data["user"]
        tokens = RefreshToken.for_user(user)

        return APIResponse.success(
            data={
                "user": UserProfileSerializer(user).data,
                "tokens": {
                    "access": str(tokens.access_token),
                    "refresh": str(tokens),
                },
            },
            message="Login successful",
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Authentication"], summary="Logout — blacklist refresh token")
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return APIResponse.error("Refresh token is required")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return APIResponse.success(message="Logged out successfully")
        except Exception as e:
            return APIResponse.error(message="Invalid or already expired token")


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Authentication"], summary="Get current user profile")
    def get(self, request):
        return APIResponse.success(data=UserProfileSerializer(request.user).data)

    @extend_schema(tags=["Authentication"], request=UserProfileSerializer, summary="Update profile")
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)
        serializer.save()
        return APIResponse.success(data=serializer.data, message="Profile updated")


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Authentication"], request=ChangePasswordSerializer, summary="Change password")
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return APIResponse.success(message="Password changed successfully")


class OTPRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(tags=["Authentication"], request=OTPRequestSerializer, summary="Request OTP")
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        try:
            user = User.objects.get(email=serializer.validated_data["email"].lower())
        except User.DoesNotExist:
            # Don't reveal if email exists
            return APIResponse.success(message="If this email exists, an OTP has been sent.")

        otp_code = user.generate_otp()
        logger.info(f"[OTP] Generated for {user.email}")

        response_data = {"otp_sent": True}
        if settings.OTP_SIMULATION_MODE:
            response_data["otp_code"] = otp_code
            logger.info(f"[OTP SIMULATION] {user.email} → {otp_code}")
        else:
            send_otp_task.delay(user.email, otp_code)

        return APIResponse.success(data=response_data, message="OTP sent successfully")


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(tags=["Authentication"], request=OTPVerifySerializer, summary="Verify OTP")
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        try:
            user = User.objects.get(email=serializer.validated_data["email"].lower())
        except User.DoesNotExist:
            raise OTPError("Invalid OTP or email")

        if not user.verify_otp(serializer.validated_data["otp"]):
            raise OTPError("Invalid or expired OTP")

        user.is_verified = True
        user.kyc_status = "VERIFIED"
        user.clear_otp()
        user.save(update_fields=["is_verified", "kyc_status"])

        return APIResponse.success(
            data=UserProfileSerializer(user).data,
            message="Account verified successfully",
        )


class NexusPayTokenRefreshView(TokenRefreshView):
    """Custom token refresh that returns user data"""

    @extend_schema(tags=["Authentication"], summary="Refresh JWT access token")
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return response
