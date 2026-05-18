"""Wallet views"""
import logging
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from core.response import APIResponse
from core.pagination import StandardResultsPagination
from .models import Wallet, WalletTransaction
from .serializers import WalletSerializer, WalletTransactionSerializer, DepositSerializer
from .services import WalletService

logger = logging.getLogger("nexuspay")


class WalletDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], summary="Get wallet details and balances")
    def get(self, request):
        try:
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            wallet = WalletService.create_wallet(request.user)
        return APIResponse.success(data=WalletSerializer(wallet).data)


class DepositView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    @extend_schema(tags=["Wallet"], request=DepositSerializer, summary="Simulate deposit")
    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        wallet = Wallet.objects.get(user=request.user)
        data = serializer.validated_data
        tx = WalletService.simulate_deposit(
            wallet=wallet,
            currency=data["currency"],
            amount=data["amount"],
            actor=request.user,
        )
        return APIResponse.created(
            data=WalletTransactionSerializer(tx).data,
            message=f"Successfully deposited {data['amount']} {data['currency']}",
        )


class WalletTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        summary="List wallet transactions",
        parameters=[
            OpenApiParameter("currency", str, description="Filter by INR or USDT"),
            OpenApiParameter("category", str, description="Filter by transaction category"),
            OpenApiParameter("status", str, description="Filter by status"),
        ],
    )
    def get(self, request):
        wallet = Wallet.objects.get(user=request.user)
        qs = WalletTransaction.objects.filter(wallet=wallet)

        # Filters
        currency = request.query_params.get("currency")
        category = request.query_params.get("category")
        status = request.query_params.get("status")
        if currency:
            qs = qs.filter(currency=currency.upper())
        if category:
            qs = qs.filter(category=category.upper())
        if status:
            qs = qs.filter(status=status.upper())

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = WalletTransactionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class WalletTransactionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], summary="Get single transaction detail")
    def get(self, request, tx_id):
        try:
            wallet = Wallet.objects.get(user=request.user)
            tx = WalletTransaction.objects.get(id=tx_id, wallet=wallet)
        except (Wallet.DoesNotExist, WalletTransaction.DoesNotExist):
            return APIResponse.not_found("Transaction not found")
        return APIResponse.success(data=WalletTransactionSerializer(tx).data)
