"""Merchant views"""
import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema

from core.response import APIResponse
from .models import Merchant, MerchantQRCode
from .serializers import (
    MerchantSerializer, RegisterMerchantSerializer,
    GenerateQRSerializer, MerchantQRCodeSerializer,
    ScanQRSerializer, SubmitTxSerializer,
)
from .services import MerchantService

logger = logging.getLogger("nexuspay")


class MerchantRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Merchant"], request=RegisterMerchantSerializer, summary="Onboard a new merchant")
    def post(self, request):
        serializer = RegisterMerchantSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)
        try:
            merchant = MerchantService.register_merchant(
                user=request.user,
                **serializer.validated_data,
            )
            return APIResponse.created(
                data=MerchantSerializer(merchant).data,
                message="Merchant registered successfully",
            )
        except ValueError as e:
            return APIResponse.error(str(e), status_code=400)


class MerchantProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Merchant"], summary="Get my merchant profile")
    def get(self, request):
        try:
            merchant = Merchant.objects.get(user=request.user)
        except Merchant.DoesNotExist:
            return APIResponse.not_found("No merchant profile found")
        return APIResponse.success(data=MerchantSerializer(merchant).data)


class GenerateQRView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    @extend_schema(tags=["Merchant"], request=GenerateQRSerializer, summary="Generate a QR payment code")
    def post(self, request):
        try:
            merchant = Merchant.objects.get(user=request.user)
        except Merchant.DoesNotExist:
            return APIResponse.not_found("No merchant profile found")

        serializer = GenerateQRSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        try:
            qr = MerchantService.generate_qr(
                merchant=merchant,
                amount_usdc=serializer.validated_data["amount_usdc"],
                description=serializer.validated_data.get("description", ""),
                expiry_seconds=serializer.validated_data.get("expiry_seconds"),
            )
            return APIResponse.created(
                data=MerchantQRCodeSerializer(qr).data,
                message="QR code generated",
            )
        except ValueError as e:
            return APIResponse.error(str(e), status_code=400)


class QRStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Merchant"], summary="Get QR code status by nonce")
    def get(self, request, nonce):
        try:
            qr = MerchantQRCode.objects.get(nonce=nonce)
        except MerchantQRCode.DoesNotExist:
            return APIResponse.not_found("QR code not found")
        return APIResponse.success(data=MerchantQRCodeSerializer(qr).data)


class ScanQRView(APIView):
    """Called when a user scans a QR code — validates and initiates payment"""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Merchant"], request=ScanQRSerializer, summary="Scan and validate a QR code")
    def post(self, request):
        serializer = ScanQRSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        try:
            qr = MerchantService.scan_qr(
                nonce=serializer.validated_data["nonce"],
                user=request.user,
            )
            return APIResponse.success(
                data=MerchantQRCodeSerializer(qr).data,
                message="QR verified. Please approve in MetaMask.",
            )
        except (ValueError, PermissionError) as e:
            return APIResponse.error(str(e), status_code=400)


class SubmitQRTransactionView(APIView):
    """Called after MetaMask broadcasts the on-chain transaction"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Merchant"],
        request=SubmitTxSerializer,
        summary="Submit blockchain tx_hash after MetaMask broadcast",
    )
    def post(self, request):
        serializer = SubmitTxSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        try:
            qr = MerchantService.submit_transaction(
                nonce=serializer.validated_data["nonce"],
                tx_hash=serializer.validated_data["tx_hash"],
                wallet_address=serializer.validated_data["wallet_address"],
                user=request.user,
            )
            return APIResponse.success(
                data=MerchantQRCodeSerializer(qr).data,
                message="Transaction submitted. Monitoring blockchain confirmations.",
            )
        except (ValueError, PermissionError) as e:
            return APIResponse.error(str(e), status_code=400)


class MerchantAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Merchant"], summary="Get merchant settlement analytics")
    def get(self, request):
        try:
            merchant = Merchant.objects.get(user=request.user)
        except Merchant.DoesNotExist:
            return APIResponse.not_found("No merchant profile found")
        return APIResponse.success(data=MerchantService.get_merchant_analytics(merchant))


class MerchantQRListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Merchant"], summary="List all QR codes for merchant")
    def get(self, request):
        try:
            merchant = Merchant.objects.get(user=request.user)
        except Merchant.DoesNotExist:
            return APIResponse.not_found("No merchant profile found")

        status_filter = request.query_params.get("status")
        qs = MerchantQRCode.objects.filter(merchant=merchant)
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        qs = qs.order_by("-created_at")[:100]

        return APIResponse.success(data=MerchantQRCodeSerializer(qs, many=True).data)
